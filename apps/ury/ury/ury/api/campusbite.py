import base64
import io
import json

import frappe
from frappe import _

COMPANY = "Atlantech Global"
DEFAULT_CUSTOMER = "Cafeteria Walk-in Guest"
ORDER_SOURCE_TAG = "CampusBite App"

# Images live under apps/ury/ury/public/campusbite/ and are served by
# Frappe at /assets/ury/campusbite/<file> — hosted on our own domain so the
# demo never depends on an external image host being reachable.
IMG_BASE = "/assets/ury/campusbite"

VENDORS = {
	"SSK": {
		"label": "South Spice Kitchen",
		"tagline": "South Indian & Biryani",
		"email": "southspice@campusbite.in",
		"phone": "+91 98450 11221",
		"warehouse": "South Spice Kitchen - Counter 1 - AG",
		"cost_center": "South Spice Kitchen - AG",
		"pos_profile": "POS-SSK",
		"hero_image": None,
		"items": [
			"SSK-001", "SSK-002", "Chicken Biryani", "Mutton Biryani",
			"Veg Kofta", "Egg Curry",
		],
		"notify_users": [
			"cashier.southspice@campusbite.demo",
			"manager.southspice@campusbite.demo",
		],
	},
	"PT": {
		"label": "Punjab Tadka",
		"tagline": "North Indian & Punjabi",
		"email": "punjabtadka@campusbite.in",
		"phone": "+91 98450 22332",
		"warehouse": "Punjab Tadka - Counter 2 - AG",
		"cost_center": "Punjab Tadka - AG",
		"pos_profile": "POS-PT",
		"hero_image": None,
		"items": [
			"PT-001", "PT-002", "Paneer Butter Masala", "Paneer Tikka", "Chicken 65",
		],
		"notify_users": [
			"cashier.punjabtadka@campusbite.demo",
			"manager.punjabtadka@campusbite.demo",
		],
	},
	"WR": {
		"label": "Wok & Roll",
		"tagline": "Chinese & Asian",
		"email": "wokandroll@campusbite.in",
		"phone": "+91 98450 33443",
		"warehouse": "Wok & Roll - Counter 3 - AG",
		"cost_center": "Wok & Roll - AG",
		"pos_profile": "POS-WR",
		"hero_image": f"{IMG_BASE}/hero_wr.jpg",
		"items": [
			"WR-001", "WR-002", "Mushroom Manchurian", "Veg Spring Roll",
			"Fish Fingers", "Prawns Fry", "Chicken Lollipop",
		],
		"notify_users": [
			"cashier.wokandroll@campusbite.demo",
			"manager.wokandroll@campusbite.demo",
		],
	},
	"BT": {
		"label": "Bean There Cafe",
		"tagline": "Cafe, Snacks & Beverages",
		"email": "beanthere@campusbite.in",
		"phone": "+91 98450 44554",
		"warehouse": "Bean There Cafe - Counter 4 - AG",
		"cost_center": "Bean There Cafe - AG",
		"pos_profile": "POS-BT",
		"hero_image": None,
		"items": [
			"BT-001", "BT-002", "Fresh Lime Soda", "Mango Juice",
			"Mixed Fruit Juice", "Orange Juice", "Watermelon Juice",
		],
		"notify_users": [
			"cashier.beanthere@campusbite.demo",
			"manager.beanthere@campusbite.demo",
		],
	},
}

# Per-item photo filenames, only for items we actually verified/downloaded a
# real, correctly-matching photo for. Anything missing here falls back to a
# category icon client-side instead of showing a wrong/mismatched photo.
ITEM_IMAGES = {
	"Paneer Tikka": "item_PaneerTikka.jpg",
	"Mixed Fruit Juice": "item_MixedFruitJuice.jpg",
}

# Demo-only coupon codes: flat percentage or flat amount off the item total.
COUPONS = {
	"WELCOME10": {"type": "percent", "value": 10, "label": "10% off"},
	"FLAT50": {"type": "flat", "value": 50, "label": "Rs.50 off"},
}


@frappe.whitelist(allow_guest=True)
def get_vendors():
	out = []
	for key, v in VENDORS.items():
		out.append({
			"key": key,
			"label": v["label"],
			"tagline": v["tagline"],
			"email": v["email"],
			"phone": v["phone"],
			"item_count": len(v["items"]),
			"hero_image": v["hero_image"],
		})
	return out


@frappe.whitelist(allow_guest=True)
def get_menu(vendor):
	v = VENDORS.get(vendor)
	if not v:
		frappe.throw(_("Unknown vendor: {0}").format(vendor))

	codes = v["items"]
	rows = frappe.get_all(
		"Item",
		filters={"item_code": ["in", codes]},
		fields=["item_code", "item_name", "standard_rate", "item_group"],
	)
	rows_by_code = {r.item_code: r for r in rows}
	ordered = []
	for c in codes:
		if c not in rows_by_code:
			continue
		row = dict(rows_by_code[c])
		row["image"] = f"{IMG_BASE}/{ITEM_IMAGES[c]}" if c in ITEM_IMAGES else None
		ordered.append(row)

	return {
		"key": vendor,
		"vendor": v["label"],
		"tagline": v["tagline"],
		"hero_image": v["hero_image"],
		"items": ordered,
	}


@frappe.whitelist(allow_guest=True)
def apply_coupon(code, item_total):
	item_total = float(item_total)
	coupon = COUPONS.get((code or "").strip().upper())
	if not coupon:
		frappe.throw(_("Invalid or expired coupon code"))
	if coupon["type"] == "percent":
		discount = round(item_total * coupon["value"] / 100)
	else:
		discount = min(coupon["value"], item_total)
	return {"code": code.strip().upper(), "label": coupon["label"], "discount": discount}


def _qr_data_uri(data_string):
	import qrcode

	img = qrcode.make(data_string, box_size=8, border=2)
	buf = io.BytesIO()
	img.save(buf, format="PNG")
	b64 = base64.b64encode(buf.getvalue()).decode()
	return f"data:image/png;base64,{b64}"


@frappe.whitelist(allow_guest=True)
def get_payment_qr(amount, ref=None):
	"""Generates a real, scannable (but non-live) UPI-style QR for the demo
	payment screen. No gateway is behind this — it's the same qrcode lib
	already used for the table QR codes, just encoding a UPI intent string.
	"""
	amount = float(amount)
	payee = "campusbite@upi"
	note = ref or "CampusBite Order"
	upi_string = (
		f"upi://pay?pa={payee}&pn=CampusBite&am={amount:.2f}&cu=INR&tn={note}"
	)
	return {"qr_data_uri": _qr_data_uri(upi_string), "upi_string": upi_string}


@frappe.whitelist(allow_guest=True)
def get_feedback_qr(invoice):
	"""QR a vendor can print on the receipt or show at the counter — scanning
	it opens the CampusBite app straight to the feedback form for that exact
	order (see `?feedback=` handling client-side).
	"""
	url = f"https://iroas.atlantechglobal.com/campusbite?feedback={invoice}"
	return {"qr_data_uri": _qr_data_uri(url), "url": url}


def _create_kot(v, inv, item_lines, remarks_note=None):
	"""Drop a real URY KOT (Kitchen Order Ticket) for every app order, so the
	kitchen/reporting side of the platform records these the same way as any
	other order — not just a Sales Invoice + a bell notification. Table/room/
	production-unit fields are left blank since the app's counters aren't
	wired into the full dine-in URY Table hierarchy; URYKOT.on_submit()
	already guards every printer/table lookup behind `if self.production`/
	`if self.restaurant_table`, so this stays safe with those left empty.
	"""
	kot = frappe.get_doc({
		"doctype": "URY KOT",
		"invoice": inv.name,
		"date": frappe.utils.nowdate(),
		"type": "New Order",
		"naming_series": "CBK-.#####.",
		"pos_profile": v["pos_profile"],
		"comments": remarks_note or "",
	})
	for code, name, qty in item_lines:
		kot.append("kot_items", {"item": code, "item_name": name, "quantity": qty})
	kot.insert(ignore_permissions=True)
	kot.submit()
	return kot.name


def _notify_vendor(v, invoice_name, table, grand_total, item_lines):
	"""Push a Notification Log to the vendor's cashier/manager the moment an
	app order lands — Frappe's core NotificationLog.after_insert already
	fires a realtime bell-update for the target user, so no extra socket
	wiring is needed here (mirrors the pattern in ury_kot_notification.py).
	"""
	subject = f"New CampusBite order — {invoice_name} — Rs.{grand_total:.0f}"
	table_line = f"Table/Counter: {table}<br>" if table else ""
	items_html = "".join(f"<li>{qty} x {name}</li>" for _code, name, qty in item_lines)
	message = (
		f"<p>🔔 New order placed via the CampusBite customer app.</p>"
		f"<p>{table_line}Invoice: {invoice_name}<br>Amount: Rs.{grand_total:.0f}</p>"
		f"<ul>{items_html}</ul>"
	)
	for user in v.get("notify_users", []):
		if not frappe.db.exists("User", user):
			continue
		frappe.get_doc({
			"doctype": "Notification Log",
			"for_user": user,
			"subject": subject,
			"email_content": message,
			"type": "Alert",
		}).insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def place_order(vendor, table=None, customer_name=None, customer_phone=None, items=None,
				remarks_note=None, coupon_code=None, discount=0):
	if isinstance(items, str):
		items = json.loads(items)

	v = VENDORS.get(vendor)
	if not v:
		frappe.throw(_("Unknown vendor: {0}").format(vendor))
	if not items:
		frappe.throw(_("Cart is empty"))

	valid_codes = set(v["items"])
	item_master = {
		r.item_code: r
		for r in frappe.get_all(
			"Item", filters={"item_code": ["in", list(valid_codes)]},
			fields=["item_code", "item_name", "standard_rate"],
		)
	}

	inv = frappe.new_doc("Sales Invoice")
	inv.company = COMPANY
	inv.customer = DEFAULT_CUSTOMER
	inv.is_pos = 1
	inv.pos_profile = v["pos_profile"]
	inv.set_warehouse = v["warehouse"]
	inv.cost_center = v["cost_center"]
	inv.update_stock = 1

	po_note = f"Source: {ORDER_SOURCE_TAG}"
	if table:
		po_note += f" | Table: {table}"
	if coupon_code:
		po_note += f" | Coupon: {coupon_code}"
	inv.po_no = po_note[:140]

	remarks_bits = [f"Order placed via {ORDER_SOURCE_TAG}"]
	if customer_name:
		remarks_bits.append(f"Customer: {customer_name}")
	if customer_phone:
		remarks_bits.append(f"Phone: {customer_phone}")
	if remarks_note:
		remarks_bits.append(f"Note: {remarks_note}")
	inv.remarks = " | ".join(remarks_bits)

	item_total = 0
	item_lines = []
	for row in items:
		code = row.get("item_code")
		qty = int(row.get("qty") or 1)
		if code not in valid_codes:
			frappe.throw(_("Item {0} is not on this vendor's menu").format(code))
		master = item_master.get(code)
		rate = master.standard_rate if master else 0
		inv.append("items", {
			"item_code": code,
			"qty": qty,
			"rate": rate,
			"warehouse": v["warehouse"],
			"cost_center": v["cost_center"],
		})
		item_total += rate * qty
		item_lines.append((code, master.item_name if master else code, qty))

	discount = float(discount or 0)
	if discount:
		inv.discount_amount = abs(discount)

	inv.append("payments", {"mode_of_payment": "UPI", "amount": max(item_total - discount, 0)})
	inv.campusbite_order_status = "Confirmed"

	inv.insert(ignore_permissions=True)
	inv.submit()

	kot_name = _create_kot(v, inv, item_lines, remarks_note)
	_notify_vendor(v, inv.name, table, inv.grand_total, item_lines)

	return {
		"invoice": inv.name,
		"kot": kot_name,
		"grand_total": inv.grand_total,
		"vendor": v["label"],
		"posting_date": str(inv.posting_date),
		"posting_time": str(inv.posting_time),
		"status": "Paid",
	}


@frappe.whitelist(allow_guest=True)
def order_status(invoice):
	doc = frappe.get_doc("Sales Invoice", invoice)
	return {
		"invoice": doc.name,
		"status": "Completed" if doc.docstatus == 1 else ("Cancelled" if doc.docstatus == 2 else "Draft"),
		"order_stage": doc.get("campusbite_order_status") or "Confirmed",
		"grand_total": doc.grand_total,
		"vendor": doc.cost_center,
		"items": [{"item_code": i.item_code, "item_name": i.item_name, "qty": i.qty, "rate": i.rate} for i in doc.items],
		"posting_date": str(doc.posting_date),
		"posting_time": str(doc.posting_time),
	}


@frappe.whitelist()
def update_order_status(invoice, status):
	"""Vendor-side action (logged-in URY Cashier/Manager/Admin only) to move
	an order through Confirmed -> Preparing -> Served. Pushed live to the
	customer app via realtime so the order tracker updates without a refresh.
	"""
	if status not in ("Confirmed", "Preparing", "Served"):
		frappe.throw(_("Invalid status: {0}").format(status))

	doc = frappe.get_doc("Sales Invoice", invoice)
	doc.db_set("campusbite_order_status", status, update_modified=False)
	frappe.publish_realtime(
		f"campusbite_order_{invoice}", {"invoice": invoice, "status": status}, after_commit=True
	)
	return {"invoice": invoice, "status": status}


def _vendor_label_for_cost_center(cost_center):
	for v in VENDORS.values():
		if v["cost_center"] == cost_center:
			return v["label"]
	return cost_center


def _phone_from_remarks(remarks):
	for part in (remarks or "").split(" | "):
		if part.startswith("Phone: "):
			return part[len("Phone: "):]
	return None


@frappe.whitelist(allow_guest=True)
def submit_feedback(invoice, rating, comment=None, item_code=None):
	rating = int(rating)
	if rating < 1 or rating > 5:
		frappe.throw(_("Rating must be between 1 and 5"))
	if frappe.db.exists("CampusBite Feedback", {"invoice": invoice, "item_code": item_code}):
		frappe.throw(_("Feedback already submitted for this order"))

	inv = frappe.get_doc("Sales Invoice", invoice)
	fb = frappe.get_doc({
		"doctype": "CampusBite Feedback",
		"invoice": invoice,
		"cost_center": inv.cost_center,
		"vendor_label": _vendor_label_for_cost_center(inv.cost_center),
		"item_code": item_code,
		"rating": rating,
		"comment": comment,
		"customer_phone": _phone_from_remarks(inv.remarks),
	})
	fb.insert(ignore_permissions=True)
	return {"name": fb.name, "status": "ok"}


@frappe.whitelist(allow_guest=True)
def get_order_history(phone):
	"""All CampusBite-app orders placed by this phone number, newest first.
	Matched via the phone number we already stamp into `remarks` on every
	app order — no separate customer-account system needed for the demo.
	"""
	phone = (phone or "").strip()
	if not phone:
		return {"orders": [], "coins": 0}

	rows = frappe.get_all(
		"Sales Invoice",
		filters={
			"remarks": ["like", f"%Phone: {phone}%"],
			"docstatus": 1,
		},
		fields=["name", "cost_center", "grand_total", "posting_date", "posting_time", "campusbite_order_status"],
		order_by="creation desc",
	)

	feedback_given = set(frappe.get_all(
		"CampusBite Feedback",
		filters={"invoice": ["in", [r.name for r in rows]]},
		pluck="invoice",
	)) if rows else set()

	orders = []
	for r in rows:
		items = frappe.get_all(
			"Sales Invoice Item",
			filters={"parent": r.name},
			fields=["item_name", "qty", "rate"],
		)
		orders.append({
			"invoice": r.name,
			"vendor": _vendor_label_for_cost_center(r.cost_center),
			"grand_total": r.grand_total,
			"posting_date": str(r.posting_date),
			"posting_time": str(r.posting_time),
			"order_stage": r.campusbite_order_status or "Confirmed",
			"has_feedback": r.name in feedback_given,
			"items": items,
		})

	return {"orders": orders, "coins": len(orders)}


@frappe.whitelist(allow_guest=True)
def get_hotel_dashboard(vendor=None):
	"""Live summary for the demo dashboard: sales, feedback, staff, peak hour
	and recent activity — either for one hotel, or "ALL" for the combined
	aggregator view. Every number here is a live query, not a snapshot.
	"""
	if vendor and vendor != "ALL":
		v = VENDORS.get(vendor)
		if not v:
			frappe.throw(_("Unknown vendor: {0}").format(vendor))
		cost_centers = [v["cost_center"]]
		pos_profiles = [v["pos_profile"]]
		label = v["label"]
	else:
		cost_centers = [x["cost_center"] for x in VENDORS.values()]
		pos_profiles = [x["pos_profile"] for x in VENDORS.values()]
		label = "All Hotels"

	inv_filters = {"cost_center": ["in", cost_centers], "docstatus": 1}

	totals = frappe.db.get_all(
		"Sales Invoice", filters=inv_filters,
		fields=["count(name) as order_count", "sum(grand_total) as total_sales"],
	)[0]

	recent = frappe.get_all(
		"Sales Invoice", filters=inv_filters,
		fields=["name", "cost_center", "grand_total", "posting_date", "posting_time", "campusbite_order_status"],
		order_by="posting_date desc, posting_time desc",
		limit=12,
	)
	recent_orders = []
	for r in recent:
		items = frappe.get_all("Sales Invoice Item", filters={"parent": r.name}, fields=["item_name", "qty"])
		recent_orders.append({
			"invoice": r.name,
			"vendor": _vendor_label_for_cost_center(r.cost_center),
			"grand_total": r.grand_total,
			"posting_date": str(r.posting_date),
			"posting_time": str(r.posting_time)[:8],
			"stage": r.campusbite_order_status or "Confirmed",
			"items": ", ".join(f"{i.qty:.0f}x {i.item_name}" for i in items),
		})

	fb_filters = {"cost_center": ["in", cost_centers]}
	fb_totals = frappe.db.get_all(
		"CampusBite Feedback", filters=fb_filters,
		fields=["count(name) as feedback_count", "avg(rating) as avg_rating"],
	)[0]
	recent_feedback = frappe.get_all(
		"CampusBite Feedback", filters=fb_filters,
		fields=["vendor_label", "rating", "comment", "creation"],
		order_by="creation desc", limit=8,
	)

	peak = frappe.db.sql(
		"""select hour(posting_time) as hr, count(name) as orders
		   from `tabSales Invoice`
		   where docstatus=1 and cost_center in %(ccs)s
		   group by hour(posting_time) order by orders desc limit 3""",
		{"ccs": cost_centers}, as_dict=True,
	)

	staff = []
	if vendor and vendor != "ALL":
		dept = f"{label} - AG"
		staff = frappe.get_all(
			"Employee", filters={"department": dept, "status": "Active"},
			fields=["employee_name", "designation"],
		)
	else:
		staff = frappe.get_all(
			"Employee", filters={"status": "Active"},
			fields=["employee_name", "designation"],
		)

	if vendor and vendor != "ALL":
		warehouses = [v["warehouse"]]
	else:
		warehouses = [x["warehouse"] for x in VENDORS.values()]
	stock = frappe.get_all(
		"Bin", filters={"warehouse": ["in", warehouses], "actual_qty": [">", 0]},
		fields=["item_code", "warehouse", "actual_qty"],
		order_by="actual_qty asc",
	)
	stock_levels = [
		{"item_code": s.item_code, "qty": s.actual_qty,
		 "vendor": _vendor_label_for_cost_center(_cost_center_for_warehouse(s.warehouse))}
		for s in stock
	]

	return {
		"label": label,
		"order_count": totals.order_count or 0,
		"total_sales": totals.total_sales or 0,
		"feedback_count": fb_totals.feedback_count or 0,
		"avg_rating": round(fb_totals.avg_rating, 1) if fb_totals.avg_rating else None,
		"peak_hours": [{"hour": p.hr, "orders": p.orders} for p in peak],
		"recent_orders": recent_orders,
		"recent_feedback": [
			{"vendor": f.vendor_label, "rating": f.rating, "comment": f.comment, "when": str(f.creation)[:16]}
			for f in recent_feedback
		],
		"staff": [{"name": s.employee_name, "role": s.designation} for s in staff],
		"stock_levels": stock_levels,
	}


def _cost_center_for_warehouse(warehouse):
	for v in VENDORS.values():
		if v["warehouse"] == warehouse:
			return v["cost_center"]
	return None


def grant_corporate_read_access():
	"""One-off maintenance: give the Corporate Management role read-only
	visibility into sales data, so the read-only demo user can see reports."""
	from frappe.permissions import add_permission, update_permission_property

	role = "Corporate Management"
	doctypes = ["Sales Invoice", "POS Invoice", "Item", "Customer"]

	for dt in doctypes:
		if not frappe.db.exists("DocType", dt):
			continue
		add_permission(dt, role, 0)
		for prop, val in [
			("read", 1), ("report", 1), ("export", 1), ("print", 1),
			("write", 0), ("create", 0), ("delete", 0),
			("submit", 0), ("cancel", 0), ("amend", 0),
		]:
			update_permission_property(dt, role, 0, prop, val)

	frappe.clear_cache()
	frappe.db.commit()
	return "granted read-only Corporate Management access on: " + ", ".join(doctypes)


@frappe.whitelist(allow_guest=True)
def get_staff_kiosk_list():
	"""Active employees for the counter check-in kiosk, with their last known
	status (whether their most recent log today was an IN or an OUT).
	"""
	employees = frappe.get_all(
		"Employee", filters={"status": "Active"},
		fields=["name", "employee_name", "designation", "department"],
		order_by="employee_name",
	)
	out = []
	for e in employees:
		last = frappe.get_all(
			"Employee Checkin", filters={"employee": e.name},
			fields=["log_type", "time"], order_by="time desc", limit=1,
		)
		out.append({
			"employee": e.name,
			"name": e.employee_name,
			"role": e.designation,
			"hotel": (e.department or "").replace(" - AG", ""),
			"currently_in": bool(last and last[0].log_type == "IN"),
			"last_time": str(last[0].time) if last else None,
		})
	return out


@frappe.whitelist(allow_guest=True)
def employee_checkin(employee, log_type):
	"""Counter kiosk action — a real Employee Checkin record, the same
	doctype used by the standard HR module's attendance reporting.
	"""
	if log_type not in ("IN", "OUT"):
		frappe.throw(_("Invalid log type: {0}").format(log_type))
	if not frappe.db.exists("Employee", employee):
		frappe.throw(_("Unknown employee"))

	doc = frappe.get_doc({
		"doctype": "Employee Checkin",
		"employee": employee,
		"log_type": log_type,
		"time": frappe.utils.now_datetime(),
	})
	doc.insert(ignore_permissions=True)
	return {"employee": employee, "log_type": log_type, "time": str(doc.time)}


@frappe.whitelist(allow_guest=True)
def ocr_read_order_number(image_base64):
	"""Proof-of-concept: reads a photographed/printed order number via OCR
	(Tesseract). This is a real, working capability — it isn't wired into a
	live physical-token workflow because this platform's orders already
	originate digitally (see place_order/get_hotel_dashboard), so there's no
	paper token in the current flow to point a camera at. Demonstrates the
	requested capability directly rather than simulating it.
	"""
	import re

	import pytesseract
	from PIL import Image

	if "," in image_base64:
		image_base64 = image_base64.split(",", 1)[1]

	raw = base64.b64decode(image_base64)
	img = Image.open(io.BytesIO(raw)).convert("L")

	raw_text = pytesseract.image_to_string(img, config="--psm 7 -c tessedit_char_whitelist=0123456789#ORDER ")
	digits = re.findall(r"\d+", raw_text)
	order_number = digits[0] if digits else None

	return {"raw_text": raw_text.strip(), "order_number": order_number}
