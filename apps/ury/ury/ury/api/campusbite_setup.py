"""One-time (idempotent) setup for CampusBite phase-2 features: custom fields,
new doctypes, reports, number cards, and the expiry-alert scheduled job.
Safe to re-run — every create step checks for existence first.
"""
import frappe


VENDOR_ROLES = ["URY Manager", "URY Cashier", "System Manager"]


def _ensure_custom_field(doctype, fieldname, df):
	name = f"{doctype}-{fieldname}"
	if frappe.db.exists("Custom Field", name):
		return
	cf = frappe.get_doc({
		"doctype": "Custom Field",
		"dt": doctype,
		"fieldname": fieldname,
		**df,
	})
	cf.insert(ignore_permissions=True)


def setup_order_status_field():
	_ensure_custom_field("Sales Invoice", "campusbite_order_status", {
		"label": "CampusBite Order Status",
		"fieldtype": "Select",
		"options": "Confirmed\nPreparing\nServed",
		"default": "Confirmed",
		"insert_after": "status",
		"in_list_view": 1,
		"in_standard_filter": 1,
		"allow_on_submit": 1,
	})


def setup_asset_ownership_field():
	if not frappe.db.exists("DocType", "Asset"):
		return
	_ensure_custom_field("Asset", "campusbite_owned_by", {
		"label": "Owned By",
		"fieldtype": "Select",
		"options": "Company\nVendor",
		"default": "Company",
		"insert_after": "asset_name",
		"in_list_view": 1,
		"in_standard_filter": 1,
	})
	_ensure_custom_field("Asset", "campusbite_owner_vendor", {
		"label": "Owner Vendor",
		"fieldtype": "Select",
		"options": "\nSouth Spice Kitchen\nPunjab Tadka\nWok & Roll\nBean There Cafe",
		"insert_after": "campusbite_owned_by",
		"depends_on": "eval:doc.campusbite_owned_by=='Vendor'",
		"in_list_view": 1,
	})


def setup_feedback_doctype():
	if frappe.db.exists("DocType", "CampusBite Feedback"):
		return

	perms = [
		{"role": role, "read": 1, "write": 1 if role != "URY Cashier" else 0,
		 "create": 1, "report": 1, "export": 1,
		 "if_owner": 0}
		for role in VENDOR_ROLES
	]
	# Guests submit via a whitelisted API (insert with ignore_permissions),
	# so no Guest DocPerm is needed here — only desk-side visibility.

	doc = frappe.get_doc({
		"doctype": "DocType",
		"name": "CampusBite Feedback",
		"module": "URY",
		"custom": 1,
		"naming_rule": "Expression (old style)",
		"autoname": "CBFB-.#####.",
		"fields": [
			{"fieldname": "invoice", "label": "Invoice", "fieldtype": "Link",
			 "options": "Sales Invoice", "reqd": 1, "in_list_view": 1},
			{"fieldname": "cost_center", "label": "Cost Center", "fieldtype": "Link",
			 "options": "Cost Center", "in_list_view": 1, "in_standard_filter": 1},
			{"fieldname": "vendor_label", "label": "Vendor", "fieldtype": "Data",
			 "read_only": 1, "in_list_view": 1},
			{"fieldname": "column_break_1", "fieldtype": "Column Break"},
			{"fieldname": "item_code", "label": "Item (optional)", "fieldtype": "Link",
			 "options": "Item"},
			{"fieldname": "rating", "label": "Rating (1-5)", "fieldtype": "Int",
			 "reqd": 1, "in_list_view": 1},
			{"fieldname": "customer_phone", "label": "Customer Phone", "fieldtype": "Data"},
			{"fieldname": "section_break_1", "fieldtype": "Section Break"},
			{"fieldname": "comment", "label": "Comment", "fieldtype": "Small Text"},
		],
		"permissions": perms,
		"sort_field": "creation",
		"sort_order": "DESC",
	})
	doc.insert(ignore_permissions=True)


def setup_entry_exit_doctype():
	if frappe.db.exists("DocType", "CampusBite Entry Exit Check"):
		return

	perms = [
		{"role": role, "read": 1, "write": 1, "create": 1, "report": 1, "export": 1}
		for role in VENDOR_ROLES
	]

	doc = frappe.get_doc({
		"doctype": "DocType",
		"name": "CampusBite Entry Exit Check",
		"module": "URY",
		"custom": 1,
		"naming_rule": "Expression (old style)",
		"autoname": "CBEX-.#####.",
		"fields": [
			{"fieldname": "cost_center", "label": "Cost Center", "fieldtype": "Link",
			 "options": "Cost Center", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
			{"fieldname": "check_type", "label": "Check Type", "fieldtype": "Select",
			 "options": "Entry\nExit", "reqd": 1, "in_list_view": 1, "in_standard_filter": 1},
			{"fieldname": "reference", "label": "Reference (order/delivery no.)",
			 "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "column_break_1", "fieldtype": "Column Break"},
			{"fieldname": "checked_at", "label": "Checked At", "fieldtype": "Datetime",
			 "default": "now", "in_list_view": 1},
			{"fieldname": "photo", "label": "Photo", "fieldtype": "Attach Image"},
			{"fieldname": "section_break_1", "fieldtype": "Section Break"},
			{"fieldname": "remarks", "label": "Remarks / Discrepancy Notes", "fieldtype": "Small Text"},
		],
		"permissions": perms,
		"sort_field": "creation",
		"sort_order": "DESC",
	})
	doc.insert(ignore_permissions=True)


def setup_number_cards():
	cards = [
		{
			"name": "CampusBite Total Sales",
			"label": "CampusBite Total Sales",
			"document_type": "Sales Invoice",
			"aggregate_function_based_on": "grand_total",
			"function": "Sum",
			"filters_json": '[["Sales Invoice","docstatus","=",1]]',
			"is_public": 1,
		},
		{
			"name": "CampusBite Orders (All Time)",
			"label": "CampusBite Orders (All Time)",
			"document_type": "Sales Invoice",
			"function": "Count",
			"filters_json": '[["Sales Invoice","docstatus","=",1]]',
			"is_public": 1,
		},
		{
			"name": "CampusBite Feedback Received",
			"label": "CampusBite Feedback Received",
			"document_type": "CampusBite Feedback",
			"function": "Count",
			"filters_json": "[]",
			"is_public": 1,
		},
	]
	for c in cards:
		if frappe.db.exists("Number Card", c["name"]):
			continue
		frappe.get_doc({"doctype": "Number Card", **c}).insert(ignore_permissions=True)


def setup_entry_exit_tally_field():
	_ensure_custom_field("CampusBite Entry Exit Check", "item_count", {
		"label": "Item Count",
		"fieldtype": "Int",
		"insert_after": "reference",
		"in_list_view": 1,
	})


def setup_feedback_by_item_report():
	name = "CampusBite Feedback by Item"
	if frappe.db.exists("Report", name):
		return
	# A whole-order rating is attributed to every item that order contained —
	# there's no separate per-item rating capture in the app, so this is the
	# honest way to roll feedback up to food-item level from what's actually
	# collected today.
	query = """
		select
			sii.item_code as "Item:Link/Item:200",
			sii.item_name as "Item Name:Data:200",
			count(distinct fb.name) as "Orders Rated:Int:120",
			round(avg(fb.rating), 2) as "Avg Rating:Float:120"
		from `tabCampusBite Feedback` fb
		join `tabSales Invoice Item` sii on sii.parent = fb.invoice
		group by sii.item_code, sii.item_name
		order by "Avg Rating:Float:120" desc
	"""
	frappe.get_doc({
		"doctype": "Report",
		"report_name": name,
		"ref_doctype": "CampusBite Feedback",
		"report_type": "Query Report",
		"is_standard": "No",
		"query": query,
		"roles": [{"role": "URY Manager"}, {"role": "System Manager"}],
	}).insert(ignore_permissions=True)


def setup_entry_exit_tally_report():
	name = "CampusBite Entry Exit Tally"
	if frappe.db.exists("Report", name):
		return
	query = """
		select
			cost_center as "Hotel:Data:200",
			reference as "Reference:Data:160",
			max(case when check_type='Entry' then item_count end) as "Entry Count:Int:110",
			max(case when check_type='Exit' then item_count end) as "Exit Count:Int:110",
			case
				when max(case when check_type='Entry' then item_count end) is null
					or max(case when check_type='Exit' then item_count end) is null then "Incomplete"
				when max(case when check_type='Entry' then item_count end)
					= max(case when check_type='Exit' then item_count end) then "Match"
				else "Discrepancy"
			end as "Status:Data:120"
		from `tabCampusBite Entry Exit Check`
		group by cost_center, reference
		order by cost_center, reference
	"""
	frappe.get_doc({
		"doctype": "Report",
		"report_name": name,
		"ref_doctype": "CampusBite Entry Exit Check",
		"report_type": "Query Report",
		"is_standard": "No",
		"query": query,
		"roles": [{"role": "URY Manager"}, {"role": "System Manager"}],
	}).insert(ignore_permissions=True)


def setup_peak_hour_report():
	name = "CampusBite Peak Hours"
	if frappe.db.exists("Report", name):
		return
	query = """
		select
			cost_center as "Hotel:Data:200",
			hour(posting_time) as "Hour of Day:Int:100",
			count(name) as "Orders:Int:100",
			sum(grand_total) as "Revenue:Currency:120"
		from `tabSales Invoice`
		where docstatus = 1
		group by cost_center, hour(posting_time)
		order by cost_center, hour(posting_time)
	"""
	frappe.get_doc({
		"doctype": "Report",
		"report_name": name,
		"ref_doctype": "Sales Invoice",
		"report_type": "Query Report",
		"is_standard": "No",
		"query": query,
		"roles": [{"role": "URY Manager"}, {"role": "System Manager"}],
	}).insert(ignore_permissions=True)


def check_expiring_batches(days_ahead=5):
	"""Scheduled job (daily): alert vendor users about consumable batches
	nearing expiry. Works the moment any vendor starts recording batch +
	expiry data on their consumable items — no data exists yet, so this
	runs as a real, tested no-op until they do.
	"""
	from frappe.utils import add_days, today

	cutoff = add_days(today(), days_ahead)
	batches = frappe.get_all(
		"Batch",
		filters={"expiry_date": ["between", [today(), cutoff]], "disabled": 0},
		fields=["name", "item", "expiry_date", "batch_qty"],
	)
	if not batches:
		return

	notify_users = frappe.get_all(
		"Has Role", filters={"role": ["in", ["URY Manager", "URY Cashier"]]}, fields=["parent"]
	)
	users = {u.parent for u in notify_users if frappe.db.get_value("User", u.parent, "enabled")}

	for b in batches:
		subject = f"Batch {b.name} ({b.item}) expires {b.expiry_date}"
		message = f"<p>Batch <b>{b.name}</b> of item <b>{b.item}</b> expires on {b.expiry_date}. Remaining qty: {b.batch_qty}.</p>"
		for user in users:
			frappe.get_doc({
				"doctype": "Notification Log",
				"for_user": user,
				"subject": subject,
				"email_content": message,
				"type": "Alert",
			}).insert(ignore_permissions=True)


def run_all():
	setup_order_status_field()
	setup_asset_ownership_field()
	setup_feedback_doctype()
	setup_entry_exit_doctype()
	setup_number_cards()
	setup_peak_hour_report()
	setup_entry_exit_tally_field()
	setup_feedback_by_item_report()
	setup_entry_exit_tally_report()
	frappe.db.commit()
	print("PHASE2_SETUP_OK")
