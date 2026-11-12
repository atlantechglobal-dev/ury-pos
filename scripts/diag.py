import frappe
print("OPS_ROLES::" + str(frappe.get_roles("ops.campusbite@campusbite.demo")))
print("SSK_CASHIER_ROLES::" + str(frappe.get_roles("cashier.southspice@campusbite.demo")))
frappe.set_user("ops.campusbite@campusbite.demo")
res = frappe.has_permission("Sales Invoice", ptype="read", debug=True)
print("HAS_PERM_RESULT::" + str(res))
print("ERROR_MSG::" + str(frappe.flags.error_message))
frappe.set_user("Administrator")
