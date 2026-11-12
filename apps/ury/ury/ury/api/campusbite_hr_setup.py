"""One-time (idempotent) HR setup for CampusBite counter staff: a Department
and Shift Type per hotel, Employee records for the existing vendor/aggregator
Users, and Shift Assignments — completing item 2 (Timesheet & Shift
Management) now that HRMS is installed.
"""
import frappe
from frappe.utils import nowdate, add_days

COMPANY = "Atlantech Global"

VENDORS = [
	("South Spice Kitchen", "09:00:00", "21:00:00"),
	("Punjab Tadka", "09:00:00", "21:00:00"),
	("Wok & Roll", "10:00:00", "22:00:00"),
	("Bean There Cafe", "08:00:00", "20:00:00"),
]

STAFF = [
	# (user, hotel_label or None for aggregator, designation)
	("cashier.southspice@campusbite.demo", "South Spice Kitchen", "Vendor Cashier"),
	("manager.southspice@campusbite.demo", "South Spice Kitchen", "Vendor Manager"),
	("cashier.punjabtadka@campusbite.demo", "Punjab Tadka", "Vendor Cashier"),
	("manager.punjabtadka@campusbite.demo", "Punjab Tadka", "Vendor Manager"),
	("cashier.wokandroll@campusbite.demo", "Wok & Roll", "Vendor Cashier"),
	("manager.wokandroll@campusbite.demo", "Wok & Roll", "Vendor Manager"),
	("cashier.beanthere@campusbite.demo", "Bean There Cafe", "Vendor Cashier"),
	("manager.beanthere@campusbite.demo", "Bean There Cafe", "Vendor Manager"),
	("ops.campusbite@campusbite.demo", None, "Aggregator Manager"),
]


def _ensure_designation(name):
	if not frappe.db.exists("Designation", name):
		frappe.get_doc({"doctype": "Designation", "designation_name": name}).insert(ignore_permissions=True)


def _ensure_department(dept_name):
	full_name = f"{dept_name} - AG"
	if not frappe.db.exists("Department", full_name):
		frappe.get_doc({
			"doctype": "Department",
			"department_name": dept_name,
			"company": COMPANY,
		}).insert(ignore_permissions=True)
	return full_name


def _ensure_shift_type(hotel_label, start_time, end_time):
	name = f"{hotel_label} Counter Shift"
	if not frappe.db.exists("Shift Type", name):
		frappe.get_doc({
			"doctype": "Shift Type",
			"name": name,
			"start_time": start_time,
			"end_time": end_time,
		}).insert(ignore_permissions=True)
	return name


def _ensure_employee(user, designation, department=None):
	existing = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if existing:
		return existing

	u = frappe.get_doc("User", user)
	_ensure_designation(designation)

	emp = frappe.get_doc({
		"doctype": "Employee",
		"first_name": u.first_name or u.full_name,
		"last_name": u.last_name or "",
		"user_id": user,
		"company": COMPANY,
		"status": "Active",
		"gender": "Prefer not to say",
		"date_of_birth": "1995-01-01",
		"date_of_joining": add_days(nowdate(), -180),
		"designation": designation,
		"department": department,
		"personal_email": user,
		"cell_number": "",
	})
	emp.insert(ignore_permissions=True)
	return emp.name


def run_all():
	shift_by_hotel = {}
	for hotel_label, start_time, end_time in VENDORS:
		dept = _ensure_department(hotel_label)
		shift = _ensure_shift_type(hotel_label, start_time, end_time)
		shift_by_hotel[hotel_label] = (dept, shift)

	_ensure_designation("Aggregator Manager")

	created = []
	for user, hotel_label, designation in STAFF:
		dept = shift_by_hotel[hotel_label][0] if hotel_label else None
		emp_name = _ensure_employee(user, designation, dept)
		created.append((user, emp_name, hotel_label))

		if hotel_label:
			shift_name = shift_by_hotel[hotel_label][1]
			already = frappe.db.exists("Shift Assignment", {
				"employee": emp_name, "shift_type": shift_name, "docstatus": ["!=", 2],
			})
			if not already:
				sa = frappe.get_doc({
					"doctype": "Shift Assignment",
					"employee": emp_name,
					"shift_type": shift_name,
					"company": COMPANY,
					"start_date": add_days(nowdate(), -30),
				})
				sa.insert(ignore_permissions=True)
				sa.submit()

	frappe.db.commit()
	for user, emp_name, hotel_label in created:
		print(f"EMPLOYEE: {emp_name} <- {user} ({hotel_label or 'Aggregator'})")
	print("HR_SETUP_OK")
