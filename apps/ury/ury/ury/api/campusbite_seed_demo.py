"""Seeds realistic demo data for tomorrow's client demo: >=10 varied orders
per hotel (with feedback on most of them), spread across the last several
days/hours so Order Log, Peak Hours, and the dashboards all look genuinely
populated rather than showing a handful of same-second test rows.

Re-running is safe — it always adds a fresh batch, doesn't touch existing data.
"""
import random

import frappe
from frappe.utils import now_datetime, add_days, get_datetime

from ury.ury.api.campusbite import VENDORS, place_order, submit_feedback

CUSTOMERS = [
	("Rahul Verma", "9820011122"),
	("Sneha Kulkarni", "9820022233"),
	("Aman Gupta", "9820033344"),
	("Divya Menon", "9820044455"),
	("Karthik Rao", "9820055566"),
	("Neha Joshi", "9820066677"),
	("Sameer Khan", "9820077788"),
	("Pooja Reddy", "9820088899"),
]

REMARKS = [None, None, "Less spicy please", "Extra napkins", "No onions", "Pack it well, taking away", None]
COMMENTS = [
	"Great taste, quick service!", "Good but a bit late today.", "Loved it, will order again.",
	"Portion could be bigger.", "Perfectly packed, tasty as always.", "Decent, nothing special.",
	"Best meal I've had here!", "Slightly cold when it arrived.", "", "",
]

TABLES = ["T-1", "T-2", "T-3", "T-4", "T-5", "Counter", "Counter"]


def _random_timestamp(days_back_max=6):
	days_back = random.randint(0, days_back_max)
	hour = random.choice([8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
	minute = random.randint(0, 59)
	dt = add_days(now_datetime(), -days_back)
	dt = get_datetime(dt).replace(hour=hour, minute=minute, second=random.randint(0, 59))
	return dt


def seed_vendor(vendor_key, count=10):
	v = VENDORS[vendor_key]
	created = []

	for i in range(count):
		customer_name, phone = random.choice(CUSTOMERS)
		items = random.sample(v["items"], k=random.choice([1, 1, 2, 2, 3]))
		payload_items = [{"item_code": code, "qty": random.choice([1, 1, 1, 2])} for code in items]

		res = place_order(
			vendor=vendor_key,
			table=random.choice(TABLES),
			customer_name=customer_name,
			customer_phone=phone,
			items=payload_items,
			remarks_note=random.choice(REMARKS),
		)
		invoice = res["invoice"]
		kot = res["kot"]

		fake_dt = _random_timestamp()
		fake_date = fake_dt.date()
		fake_time = fake_dt.time()

		# Vary the order's stage — mostly Served (a completed history), a few
		# still Confirmed/Preparing so the live tracker has something to show.
		stage = random.choices(["Served", "Preparing", "Confirmed"], weights=[7, 2, 1])[0]

		frappe.db.set_value("Sales Invoice", invoice, {
			"posting_date": fake_date,
			"posting_time": fake_time,
			"campusbite_order_status": stage,
		}, update_modified=False)
		frappe.db.sql(
			"update `tabSales Invoice` set creation=%s, modified=%s where name=%s",
			(fake_dt, fake_dt, invoice),
		)
		frappe.db.set_value("URY KOT", kot, {"date": fake_date}, update_modified=False)
		frappe.db.sql(
			"update `tabURY KOT` set creation=%s, modified=%s where name=%s",
			(fake_dt, fake_dt, kot),
		)

		# Feedback on most (not all) orders, so a couple are left for a live
		# "rate this order" demo.
		if stage == "Served" and random.random() < 0.8:
			rating = random.choices([5, 4, 3], weights=[5, 3, 1])[0]
			comment = random.choice(COMMENTS)
			fb = submit_feedback(invoice=invoice, rating=rating, comment=comment or None)
			fb_dt = fake_dt
			frappe.db.sql(
				"update `tabCampusBite Feedback` set creation=%s, modified=%s where name=%s",
				(fb_dt, fb_dt, fb["name"]),
			)

		created.append(invoice)

	return created


def run_all(per_hotel=10):
	frappe.db.commit()
	summary = {}
	for key in VENDORS:
		invoices = seed_vendor(key, count=per_hotel)
		summary[key] = len(invoices)
	frappe.db.commit()
	for key, n in summary.items():
		print(f"SEEDED {n} orders for {VENDORS[key]['label']}")
	print("SEED_OK")
