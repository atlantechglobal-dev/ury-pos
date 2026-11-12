import frappe
c = frappe.get_doc("Company", "Atlantech Global")
print("ABBR::" + c.abbr)
print("COST_CENTER::" + str(c.cost_center))
print("MOP::" + str([d.name for d in frappe.get_all("Mode of Payment")]))
print("SUPGRP::" + str([d.name for d in frappe.get_all("Supplier Group")]))
print("ITEMGRP::" + str([d.name for d in frappe.get_all("Item Group")]))
print("WH::" + str([d.name for d in frappe.get_all("Warehouse")]))
print("ROLES::" + str([d.name for d in frappe.get_all("Role", filters={"name":["in",["Sales User","Sales Manager","Accounts Manager","Accounts User"]]})]))
