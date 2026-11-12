import frappe
frappe.set_user("cashier.southspice@campusbite.demo")
visible = frappe.get_list("Sales Invoice", fields=["name","grand_total"], filters={"docstatus":1})
print("SSK_CASHIER_SEES::" + str(visible))
frappe.set_user("Administrator")

frappe.set_user("ops.campusbite@campusbite.demo")
all_visible = frappe.get_list("Sales Invoice", fields=["name","grand_total"], filters={"docstatus":1})
print("AGGREGATOR_SEES::" + str(len(all_visible)) + " invoices")
frappe.set_user("Administrator")

corp_perms = frappe.get_all("Custom DocPerm", filters={"role":"Corporate Management"}, fields=["parent","read","write","create","delete"])
print("CORPORATE_PERMS::" + str(corp_perms))
