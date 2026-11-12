"""Seeds demo-ready operational data so every dashboard/report has real
records to show, not empty lists: Assets (company + vendor owned),
Entry/Exit photo checks, Employee Checkins (login/logout), and real
consumable batches with expiry dates.
"""
import random

import frappe
from frappe.utils import nowdate, add_days, now_datetime, get_datetime

COMPANY = "Atlantech Global"

VENDORS = [
	("South Spice Kitchen", "South Spice Kitchen - AG", "POS-SSK"),
	("Punjab Tadka", "Punjab Tadka - AG", "POS-PT"),
	("Wok & Roll", "Wok & Roll - AG", "POS-WR"),
	("Bean There Cafe", "Bean There Cafe - AG", "POS-BT"),
]

ASSETS = [
	# (item_code, item_name, hotel_label, owned_by, purchase_amount, days_ago)
	("EQ-POS-01", "POS Terminal", "South Spice Kitchen", "Company", 28000, 400),
	("EQ-FRIDGE-01", "Commercial Refrigerator", "South Spice Kitchen", "Vendor", 65000, 620),
	("EQ-POS-02", "POS Terminal", "Punjab Tadka", "Company", 28000, 310),
	("EQ-COOKTOP-01", "Induction Cooktop", "Punjab Tadka", "Vendor", 42000, 500),
	("EQ-POS-03", "POS Terminal", "Wok & Roll", "Company", 28000, 250),
	("EQ-FRYER-01", "Commercial Deep Fryer", "Wok & Roll", "Vendor", 38000, 380),
	("EQ-POS-04", "POS Terminal", "Bean There Cafe", "Company", 28000, 180),
	("EQ-COFFEE-01", "Coffee Machine", "Bean There Cafe", "Vendor", 95000, 720),
]

CONSUMABLES = [
	("CON-MILK", "Milk (Bulk)", "Bean There Cafe"),
	("CON-PANEER", "Paneer (Bulk)", "Punjab Tadka"),
	("CON-CHICKEN", "Chicken (Raw, Bulk)", "South Spice Kitchen"),
	("CON-SAUCE", "Soy Sauce (Bulk)", "Wok & Roll"),
]


def _ensure_asset_category():
	if not frappe.db.exists("Asset Category", "Cafeteria Equipment"):
		frappe.get_doc({
			"doctype": "Asset Category",
			"asset_category_name": "Cafeteria Equipment",
			"accounts": [{
				"company_name": COMPANY,
				"fixed_asset_account": "Capital Equipments - AG",
				"accumulated_depreciation_account": "Accumulated Depreciations - AG",
				"depreciation_expense_account": "Depreciation - AG",
			}],
		}).insert(ignore_permissions=True)
	return "Cafeteria Equipment"


def _ensure_location(hotel_label):
	name = f"{hotel_label} Counter"
	if not frappe.db.exists("Location", name):
		frappe.get_doc({
			"doctype": "Location",
			"location_name": name,
		}).insert(ignore_permissions=True)
	return name


def _ensure_fixed_asset_item(item_code, item_name, category):
	if frappe.db.exists("Item", item_code):
		return
	frappe.get_doc({
		"doctype": "Item",
		"item_code": item_code,
		"item_name": item_name,
		"item_group": "Products",
		"is_fixed_asset": 1,
		"is_stock_item": 0,
		"asset_category": category,
		"stock_uom": "Nos",
	}).insert(ignore_permissions=True)


def _cost_center_for(hotel_label):
	for label, cc, _pp in VENDORS:
		if label == hotel_label:
			return cc
	return None


def seed_assets():
	category = _ensure_asset_category()
	created = 0
	for item_code, item_name, hotel_label, owned_by, amount, days_ago in ASSETS:
		_ensure_fixed_asset_item(item_code, item_name, category)
		location = _ensure_location(hotel_label)
		asset_name = f"{item_name} — {hotel_label}"

		if frappe.db.exists("Asset", {"asset_name": asset_name}):
			continue

		asset = frappe.get_doc({
			"doctype": "Asset",
			"asset_name": asset_name,
			"item_code": item_code,
			"asset_category": category,
			"company": COMPANY,
			"location": location,
			"purchase_date": add_days(nowdate(), -days_ago),
			"available_for_use_date": add_days(nowdate(), -days_ago),
			"gross_purchase_amount": amount,
			"is_existing_asset": 1,
			"asset_owner": "Company" if owned_by == "Company" else "Supplier",
			"cost_center": _cost_center_for(hotel_label),
			"campusbite_owned_by": owned_by,
			"campusbite_owner_vendor": hotel_label if owned_by == "Vendor" else "",
		})
		asset.insert(ignore_permissions=True)
		try:
			asset.submit()
		except Exception:
			pass  # still visible as a draft record if submission needs extra setup
		created += 1
	return created


def seed_entry_exit_checks(per_hotel=3):
	created = 0
	for label, cost_center, _pp in VENDORS:
		for i in range(per_hotel):
			ref = f"Delivery batch {i+1}"
			for check_type in ("Entry", "Exit"):
				doc = frappe.get_doc({
					"doctype": "CampusBite Entry Exit Check",
					"cost_center": cost_center,
					"check_type": check_type,
					"reference": ref,
					"checked_at": add_days(now_datetime(), -random.randint(0, 5)),
					"remarks": "Counts matched, no discrepancy." if check_type == "Exit" else "",
				})
				doc.insert(ignore_permissions=True)
				created += 1
	return created


def seed_employee_checkins(days_back=7):
	employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=["name", "user_id"])
	created = 0
	for emp in employees:
		for d in range(days_back):
			day = add_days(nowdate(), -d)
			in_time = get_datetime(f"{day} 09:0{random.randint(0,5)}:00")
			out_time = get_datetime(f"{day} 20:{random.randint(10,55)}:00")
			for log_type, ts in (("IN", in_time), ("OUT", out_time)):
				frappe.get_doc({
					"doctype": "Employee Checkin",
					"employee": emp.name,
					"log_type": log_type,
					"time": ts,
				}).insert(ignore_permissions=True)
				created += 1
	return created


def seed_consumable_batches():
	created = 0
	for code, name, hotel_label in CONSUMABLES:
		if not frappe.db.exists("Item", code):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": code,
				"item_name": name,
				"item_group": "Consumable",
				"is_stock_item": 1,
				"has_batch_no": 1,
				"has_expiry_date": 1,
				"stock_uom": "Kg",
			}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Item", code, {"has_batch_no": 1, "has_expiry_date": 1})

		# One batch already near expiry (for the alert job to catch), one fresh.
		for suffix, days_to_expiry, qty in [("A", 3, 12), ("B", 45, 30)]:
			batch_id = f"{code}-BATCH-{suffix}"
			if frappe.db.exists("Batch", batch_id):
				continue
			frappe.get_doc({
				"doctype": "Batch",
				"batch_id": batch_id,
				"item": code,
				"expiry_date": add_days(nowdate(), days_to_expiry),
				"batch_qty": qty,
			}).insert(ignore_permissions=True)
			created += 1
	return created


def run_all():
	n_assets = seed_assets()
	n_ee = seed_entry_exit_checks()
	n_checkins = seed_employee_checkins()
	n_batches = seed_consumable_batches()
	frappe.db.commit()
	print(f"ASSETS: {n_assets}")
	print(f"ENTRY_EXIT_CHECKS: {n_ee}")
	print(f"EMPLOYEE_CHECKINS: {n_checkins}")
	print(f"CONSUMABLE_BATCHES: {n_batches}")
	print("OPS_SEED_OK")
