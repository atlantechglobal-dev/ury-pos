import frappe
import json

def execute():
    out = {}
    out["companies"] = frappe.get_all("Company", fields=["name", "abbr", "default_currency"])
    out["branches"] = frappe.get_all("Branch", fields=["name"])
    out["warehouses"] = frappe.get_all("Warehouse", fields=["name"])
    out["price_lists"] = frappe.get_all("Price List", fields=["name", "selling"])
    out["pos_profiles"] = frappe.get_all("POS Profile", fields=["name"])
    out["item_groups"] = frappe.get_all("Item Group", fields=["name"])
    out["ury_rooms"] = frappe.get_all("URY Room", fields=["name"])
    out["ury_restaurants"] = frappe.get_all("URY Restaurant", fields=["name"])
    out["users"] = frappe.get_all("User", filters={"user_type": "System User"}, fields=["name"])
    out["cost_centers"] = frappe.get_all("Cost Center", fields=["name"])
    out["accounts_write_off"] = frappe.get_all("Account", filters={"account_name": ["like", "%Write Off%"]}, fields=["name"])
    print(json.dumps(out, indent=2))
