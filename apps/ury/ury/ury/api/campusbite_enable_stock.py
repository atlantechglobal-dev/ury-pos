"""Enables real dish-level stock tracking for CampusBite:
1. Flips is_stock_item on every dish item (safe — verified every existing
   invoice referencing these items came through CampusBite testing, not a
   separate live business process).
2. Receipts generous opening stock into each hotel's counter warehouse so
   switching on stock deduction doesn't throw Insufficient Stock errors on
   the very next order.
Does NOT touch place_order's update_stock flag — that's flipped separately
in campusbite.py once this data is confirmed in place.
"""
import frappe
from frappe.utils import nowdate

from ury.ury.api.campusbite import VENDORS

COMPANY = "Atlantech Global"
OPENING_QTY = 200


def flip_stock_items():
	changed = []
	for v in VENDORS.values():
		for code in v["items"]:
			if not frappe.db.exists("Item", code):
				continue
			is_stock = frappe.db.get_value("Item", code, "is_stock_item")
			if not is_stock:
				frappe.db.set_value("Item", code, "is_stock_item", 1)
				changed.append(code)
	return changed


def receipt_opening_stock():
	created = []
	for key, v in VENDORS.items():
		warehouse = v["warehouse"]
		items = [c for c in v["items"] if frappe.db.exists("Item", c)]
		if not items:
			continue

		se = frappe.get_doc({
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": COMPANY,
			"posting_date": nowdate(),
		})
		for code in items:
			rate = frappe.db.get_value("Item", code, "standard_rate") or 100
			se.append("items", {
				"item_code": code,
				"qty": OPENING_QTY,
				"t_warehouse": warehouse,
				"basic_rate": round(float(rate) * 0.4, 2),
			})
		se.insert(ignore_permissions=True)
		se.submit()
		created.append(se.name)
	return created


def run_all():
	changed = flip_stock_items()
	receipts = receipt_opening_stock()
	frappe.db.commit()
	print(f"STOCK_ITEMS_FLIPPED: {len(changed)} -> {changed}")
	print(f"STOCK_RECEIPTS: {receipts}")
	print("STOCK_ENABLE_OK")
