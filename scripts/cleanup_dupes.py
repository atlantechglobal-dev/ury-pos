import frappe
rows = frappe.get_all("Sales Invoice", filters={"customer":"Cafeteria Walk-in Guest"}, fields=["name","docstatus","is_return"], order_by="creation asc")
print("ALL_SI::" + str(rows))
keep = {"ACC-SINV-2026-00006","ACC-SINV-2026-00007","ACC-SINV-2026-00008","ACC-SINV-2026-00009","ACC-SINV-2026-00010"}
for r in rows:
    if r["name"] not in keep:
        try:
            doc = frappe.get_doc("Sales Invoice", r["name"])
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("Sales Invoice", r["name"], force=True, ignore_permissions=True)
            print("DELETED::" + r["name"])
        except Exception as e:
            print("DELETE_FAIL::" + r["name"] + " :: " + str(e))
frappe.db.commit()
remaining = frappe.get_all("Sales Invoice", filters={"customer":"Cafeteria Walk-in Guest"}, fields=["name","docstatus","is_return","grand_total"], order_by="creation asc")
print("REMAINING::" + str(remaining))
