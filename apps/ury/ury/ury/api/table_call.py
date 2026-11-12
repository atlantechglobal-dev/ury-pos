import frappe
from frappe import _
from frappe.utils import now_datetime

REQUEST_TYPES = {"Call Waiter", "Water", "Bill", "Cancel"}
MANAGER_ROLES = {"System Manager", "URY Manager"}
NOTIFY_ROLES = {"System Manager", "URY Manager", "Administrator"}


def get_notify_users(waiter=None):
	"""Users who should be pushed a realtime alert for a table call: the
	waiter currently serving that table, plus every Manager/Admin — so a
	request never gets silently missed if the assigned waiter is unreachable.
	"""
	users = set(
		frappe.get_all(
			"Has Role",
			filters={"role": ["in", list(MANAGER_ROLES)], "parenttype": "User"},
			pluck="parent",
		)
	)
	if frappe.db.exists("User", "Administrator"):
		users.add("Administrator")
	if waiter:
		users.add(waiter)
	return users


def get_current_waiter(table_name):
	"""Best-effort lookup of who is currently serving a table, from its
	active (unsubmitted) POS Invoice."""
	return frappe.db.get_value(
		"POS Invoice",
		{"restaurant_table": table_name, "docstatus": 0},
		"waiter",
		order_by="creation desc",
	)


def _create_call_request(table_name, request_type, device_id=None):
	waiter = get_current_waiter(table_name)

	doc = frappe.get_doc({
		"doctype": "URY Table Call Request",
		"table": table_name,
		"device_id": device_id,
		"request_type": request_type,
		"waiter": waiter,
		"status": "Open",
		"requested_on": now_datetime(),
	})
	doc.insert(ignore_permissions=True)
	frappe.db.commit()

	message = {
		"name": doc.name,
		"table": table_name,
		"request_type": request_type,
		"waiter": waiter,
		"requested_on": str(doc.requested_on),
	}
	for user in get_notify_users(waiter):
		frappe.publish_realtime("ury_table_call_request", message, user=user)

	return doc


@frappe.whitelist(allow_guest=True)
def receive_call_request(device_id, request_type):
	"""Webhook hit directly by the table-side call button device/gateway."""
	if request_type not in REQUEST_TYPES:
		frappe.throw(_("Invalid request type: {0}").format(request_type))

	table_name = frappe.db.get_value("URY Table", {"custom_device_id": device_id}, "name")
	if not table_name:
		frappe.throw(_("No table is linked to device {0}").format(device_id))

	doc = _create_call_request(table_name, request_type, device_id=device_id)
	return {"status": "ok", "name": doc.name}


@frappe.whitelist()
def create_manual_call_request(table, request_type):
	"""Staff-triggered equivalent of the device webhook — used when there is
	no physical call-button device, e.g. a captain/manager raising a request
	on the customer's behalf from within the POS Table view."""
	if request_type not in REQUEST_TYPES:
		frappe.throw(_("Invalid request type: {0}").format(request_type))

	if not frappe.db.exists("URY Table", table):
		frappe.throw(_("Table {0} not found").format(table))

	doc = _create_call_request(table, request_type)
	return {"status": "ok", "name": doc.name}


@frappe.whitelist()
def resolve_call_request(name):
	doc = frappe.get_doc("URY Table Call Request", name)
	if doc.status == "Resolved":
		return doc.as_dict()

	user_roles = set(frappe.get_roles())
	if frappe.session.user != doc.waiter and not (MANAGER_ROLES & user_roles):
		frappe.throw(_("Only the assigned waiter, a Manager, or Administrator can resolve this request"), frappe.PermissionError)

	doc.resolved_on = now_datetime()
	doc.resolved_by = frappe.session.user
	doc.status = "Resolved"
	doc.response_time = (doc.resolved_on - doc.requested_on).total_seconds()
	doc.save(ignore_permissions=True)
	frappe.db.commit()

	message = {"name": doc.name, "resolved_by": doc.resolved_by}
	for user in get_notify_users(doc.waiter):
		frappe.publish_realtime("ury_table_call_resolved", message, user=user)

	return doc.as_dict()


@frappe.whitelist()
def get_site_name():
	"""Used by the frontend to open a realtime socket under the correct
	namespace — nginx pins the socketio namespace to the actual site name
	regardless of which hostname/IP the browser used to reach the server."""
	return frappe.local.site


@frappe.whitelist()
def get_open_call_requests():
	user_roles = set(frappe.get_roles())
	filters = {"status": "Open"}
	if not (MANAGER_ROLES & user_roles):
		filters["waiter"] = frappe.session.user

	return frappe.get_all(
		"URY Table Call Request",
		filters=filters,
		fields=["name", "table", "request_type", "waiter", "requested_on"],
		order_by="requested_on asc",
	)
