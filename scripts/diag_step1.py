import frappe
u = frappe.get_doc("User", "cashier.southspice@campusbite.demo")
print("ENABLED::" + str(u.enabled))
print("ROLES::" + str([r.role for r in u.roles]))

pos = frappe.get_doc("POS Profile", "POS-SSK")
print("POS_DISABLED::" + str(pos.disabled))
print("POS_APPLICABLE_USERS::" + str([r.user for r in pos.applicable_for_users]))
print("POS_COMPANY::" + str(pos.company))
print("POS_WAREHOUSE::" + str(pos.warehouse))
print("POS_PAYMENTS::" + str([(p.mode_of_payment, p.default) for p in pos.payments]))

frappe.set_user("cashier.southspice@campusbite.demo")
try:
    from erpnext.accounts.doctype.pos_profile.pos_profile import pos_profile_query
    res = pos_profile_query("POS Profile", "", "name", 0, 20, {"company":"Atlantech Global"})
    print("QUERY_RESULT::" + str(res))
except Exception as e:
    print("QUERY_ERROR::" + str(e))
frappe.set_user("Administrator")
