import json
import random
import string

import frappe

WS_NAME = "CampusBite Aggregator"

VENDORS = [
	("South Spice Kitchen", "South Spice Kitchen - AG", "POS-SSK"),
	("Punjab Tadka", "Punjab Tadka - AG", "POS-PT"),
	("Wok & Roll", "Wok & Roll - AG", "POS-WR"),
	("Bean There Cafe", "Bean There Cafe - AG", "POS-BT"),
]


def create_workspace():
	if frappe.db.exists("Workspace", WS_NAME):
		frappe.delete_doc("Workspace", WS_NAME, force=True, ignore_permissions=True)
		frappe.db.commit()

	content = []
	shortcuts = []

	def block(type_, data, col=12):
		bid = "".join(random.choices(string.ascii_letters + string.digits, k=10))
		data = dict(data)
		data["col"] = col
		content.append({"id": bid, "type": type_, "data": data})

	def shortcut(label, type_, link_to, doc_view="Report Builder", stats_filter=None, color="Blue"):
		shortcuts.append({
			"label": label, "type": type_, "link_to": link_to, "doc_view": doc_view,
			"stats_filter": json.dumps(stats_filter) if stats_filter is not None else "",
			"color": color,
		})

	block("header", {"text": '<span class="h4"><b>CampusBite — At a Glance</b></span>'})
	block("number_card", {"number_card_name": "CampusBite Total Sales"}, col=4)
	block("number_card", {"number_card_name": "CampusBite Orders (All Time)"}, col=4)
	block("number_card", {"number_card_name": "CampusBite Feedback Received"}, col=4)
	block("spacer", {})

	block("header", {"text": '<span class="h4"><b>Peak-Hour &amp; Item Analytics</b></span>'})
	shortcut("Peak Hours by Hotel", "Report", "CampusBite Peak Hours", doc_view="", color="Grey")
	block("shortcut", {"shortcut_name": "Peak Hours by Hotel"}, col=6)
	shortcut("Top Selling Items", "Report", "Item-wise Sales Register", doc_view="", color="Grey")
	block("shortcut", {"shortcut_name": "Top Selling Items"}, col=6)
	block("spacer", {})

	block("header", {"text": '<span class="h4"><b>Hotel-wise Billing &amp; Kitchen Tickets</b></span>'})
	block("paragraph", {"text": "Owner/Admin view — each hotel's billing and kitchen tickets, kept separate."})

	for label, cost_center, pos_profile in VENDORS:
		block("header", {"text": f'<span class="h5"><b>{label}</b></span>'})

		shortcut(f"{label} — Billing", "DocType", "Sales Invoice",
				 stats_filter={"cost_center": cost_center, "docstatus": 1}, color="Blue")
		block("shortcut", {"shortcut_name": f"{label} — Billing"}, col=6)

		shortcut(f"{label} — Kitchen Tickets", "DocType", "URY KOT",
				 stats_filter={"pos_profile": pos_profile, "docstatus": 1}, color="Green")
		block("shortcut", {"shortcut_name": f"{label} — Kitchen Tickets"}, col=6)

		block("spacer", {})

	block("header", {"text": '<span class="h5"><b>All Hotels Combined</b></span>'})
	shortcut("All Hotels — Billing", "DocType", "Sales Invoice", stats_filter={"docstatus": 1}, color="Grey")
	block("shortcut", {"shortcut_name": "All Hotels — Billing"}, col=6)
	shortcut("All Hotels — Kitchen Tickets", "DocType", "URY KOT", stats_filter={"docstatus": 1}, color="Grey")
	block("shortcut", {"shortcut_name": "All Hotels — Kitchen Tickets"}, col=6)
	block("spacer", {})

	block("header", {"text": '<span class="h4"><b>Customer Feedback</b></span>'})
	for label, cost_center, pos_profile in VENDORS:
		shortcut(f"{label} — Feedback", "DocType", "CampusBite Feedback",
				 stats_filter={"cost_center": cost_center}, color="Yellow")
		block("shortcut", {"shortcut_name": f"{label} — Feedback"}, col=3)
	shortcut("All Hotels — Feedback", "DocType", "CampusBite Feedback", color="Grey")
	block("shortcut", {"shortcut_name": "All Hotels — Feedback"}, col=3)
	block("spacer", {})

	block("header", {"text": '<span class="h4"><b>Entry / Exit Product Verification</b></span>'})
	block("paragraph", {"text": "Photo capture at entry &amp; exit per hotel — paired records for manual discrepancy review."})
	for label, cost_center, pos_profile in VENDORS:
		shortcut(f"{label} — Entry/Exit Checks", "DocType", "CampusBite Entry Exit Check",
				 stats_filter={"cost_center": cost_center}, color="Grey")
		block("shortcut", {"shortcut_name": f"{label} — Entry/Exit Checks"}, col=3)
	shortcut("All Hotels — Entry/Exit Checks", "DocType", "CampusBite Entry Exit Check", color="Grey")
	block("shortcut", {"shortcut_name": "All Hotels — Entry/Exit Checks"}, col=3)

	block("header", {"text": '<span class="h4"><b>Assets</b></span>'})
	shortcut("All Assets (Company + Vendor)", "DocType", "Asset", color="Grey")
	block("shortcut", {"shortcut_name": "All Assets (Company + Vendor)"}, col=6)

	ws = frappe.get_doc({
		"doctype": "Workspace",
		"name": WS_NAME,
		"label": WS_NAME,
		"title": WS_NAME,
		"module": "URY",
		"public": 1,
		"is_hidden": 0,
		"content": json.dumps(content),
		"shortcuts": shortcuts,
	})
	ws.insert(ignore_permissions=True)
	frappe.db.commit()
	print("CREATED:", ws.name, "with", len(shortcuts), "shortcuts")
