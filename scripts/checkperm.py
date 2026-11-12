import frappe
rows = frappe.get_all("DocPerm", filters={"parent":"Sales Invoice"}, fields=["role","read","write","permlevel"])
print("SI_DOCPERM::" + str(rows))
rows2 = frappe.get_all("Custom DocPerm", filters={"parent":"Sales Invoice"}, fields=["role","read","write","permlevel"])
print("SI_CUSTOMDOCPERM::" + str(rows2))
