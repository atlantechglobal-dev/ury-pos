import frappe
from frappe.utils import nowdate

def ok(msg):
    print("OK   :: " + msg)

def fail(msg, e):
    print("FAIL :: " + msg + " :: " + str(e))

COMPANY = "Atlantech Global"
ABBR = "AG"

VENDORS = [
    {"key": "SSK", "name": "South Spice Kitchen", "counter": "Counter 1", "sup_email": "meena.pillai@southspice.demo"},
    {"key": "PT", "name": "Punjab Tadka", "counter": "Counter 2", "sup_email": "gurpreet.singh@punjabtadka.demo"},
    {"key": "WR", "name": "Wok & Roll", "counter": "Counter 3", "sup_email": "mei.lin@wokandroll.demo"},
    {"key": "BT", "name": "Bean There Cafe", "counter": "Counter 4", "sup_email": "farhan.ali@beanthere.demo"},
]

ITEMS = [
    {"code": "SSK-001", "name": "Veg Thali", "vendor": "SSK", "rate": 150},
    {"code": "SSK-002", "name": "Masala Dosa", "vendor": "SSK", "rate": 90},
    {"code": "PT-001", "name": "Butter Chicken", "vendor": "PT", "rate": 220},
    {"code": "PT-002", "name": "Dal Makhani", "vendor": "PT", "rate": 140},
    {"code": "WR-001", "name": "Veg Fried Rice", "vendor": "WR", "rate": 160},
    {"code": "WR-002", "name": "Hakka Noodles", "vendor": "WR", "rate": 150},
    {"code": "BT-001", "name": "Cold Coffee", "vendor": "BT", "rate": 80},
    {"code": "BT-002", "name": "Club Sandwich", "vendor": "BT", "rate": 70},
]

USERS = [
    {"email": "cashier.southspice@campusbite.demo", "first": "Priya", "last": "Nair", "roles": ["Sales User"], "vendor": "SSK"},
    {"email": "manager.southspice@campusbite.demo", "first": "Ananya", "last": "Iyer", "roles": ["Sales User", "Sales Manager"], "vendor": "SSK"},
    {"email": "cashier.punjabtadka@campusbite.demo", "first": "Rohit", "last": "Sharma", "roles": ["Sales User"], "vendor": "PT"},
    {"email": "manager.punjabtadka@campusbite.demo", "first": "Simran", "last": "Kaur", "roles": ["Sales User", "Sales Manager"], "vendor": "PT"},
    {"email": "cashier.wokandroll@campusbite.demo", "first": "Li", "last": "Chen", "roles": ["Sales User"], "vendor": "WR"},
    {"email": "manager.wokandroll@campusbite.demo", "first": "Arjun", "last": "Mehta", "roles": ["Sales User", "Sales Manager"], "vendor": "WR"},
    {"email": "cashier.beanthere@campusbite.demo", "first": "Fatima", "last": "Sheikh", "roles": ["Sales User"], "vendor": "BT"},
    {"email": "manager.beanthere@campusbite.demo", "first": "Karan", "last": "Malhotra", "roles": ["Sales User", "Sales Manager"], "vendor": "BT"},
    {"email": "ops.campusbite@campusbite.demo", "first": "Vikram", "last": "Desai", "roles": ["Sales Manager", "Accounts Manager"], "vendor": None},
    {"email": "admin.orion@techpark.demo", "first": "Neha", "last": "Kapoor", "roles": ["Corporate Management"], "vendor": None},
]

DEMO_PASSWORD = "Demo@Cafeteria2026"

state = {}  # vendor_key -> {cost_center, warehouse, supplier, price_list, pos_profile}

def run():
    print("=== STEP 1-2: Cost Centers & Warehouses ===")
    company_doc = frappe.get_doc("Company", COMPANY)
    parent_cc = frappe.db.get_value(
        "Cost Center",
        {"company": COMPANY, "is_group": 1, "cost_center_name": ["like", f"{COMPANY}%"]},
        "name",
    ) or frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 1}, "name")
    parent_wh = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 1, "warehouse_name": ["like", "All Warehouses%"]}, "name") or f"All Warehouses - {ABBR}"

    for v in VENDORS:
        state[v["key"]] = {}
        try:
            existing = frappe.db.get_value("Cost Center", {"cost_center_name": v["name"], "company": COMPANY})
            if existing:
                state[v["key"]]["cost_center"] = existing
                ok(f"Cost Center exists: {existing}")
            else:
                cc = frappe.get_doc({
                    "doctype": "Cost Center",
                    "cost_center_name": v["name"],
                    "parent_cost_center": parent_cc,
                    "company": COMPANY,
                    "is_group": 0,
                })
                cc.insert(ignore_permissions=True)
                state[v["key"]]["cost_center"] = cc.name
                ok(f"Cost Center created: {cc.name}")
        except Exception as e:
            fail(f"Cost Center {v['name']}", e)
            state[v["key"]]["cost_center"] = None

        try:
            wh_name = f"{v['name']} - {v['counter']}"
            existing_wh = frappe.db.get_value("Warehouse", {"warehouse_name": wh_name, "company": COMPANY})
            if existing_wh:
                state[v["key"]]["warehouse"] = existing_wh
                ok(f"Warehouse exists: {existing_wh}")
            else:
                wh = frappe.get_doc({
                    "doctype": "Warehouse",
                    "warehouse_name": wh_name,
                    "parent_warehouse": parent_wh,
                    "company": COMPANY,
                })
                wh.insert(ignore_permissions=True)
                state[v["key"]]["warehouse"] = wh.name
                ok(f"Warehouse created: {wh.name}")
        except Exception as e:
            fail(f"Warehouse {v['name']}", e)
            state[v["key"]]["warehouse"] = None
    frappe.db.commit()

    print("\n=== STEP 3: Supplier Group ===")
    try:
        if not frappe.db.exists("Supplier Group", "Cafeteria Vendors"):
            sg = frappe.get_doc({
                "doctype": "Supplier Group",
                "supplier_group_name": "Cafeteria Vendors",
                "parent_supplier_group": "All Supplier Groups",
            })
            sg.insert(ignore_permissions=True)
            ok("Supplier Group created: Cafeteria Vendors")
        else:
            ok("Supplier Group already exists: Cafeteria Vendors")
    except Exception as e:
        fail("Supplier Group Cafeteria Vendors", e)
    frappe.db.commit()

    print("\n=== STEP 4: Suppliers (Vendor Master) ===")
    for v in VENDORS:
        try:
            if frappe.db.exists("Supplier", v["name"]):
                state[v["key"]]["supplier"] = v["name"]
                ok(f"Supplier exists: {v['name']}")
                continue
            sup = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": v["name"],
                "supplier_group": "Cafeteria Vendors",
                "supplier_type": "Company",
                "country": "India",
            })
            sup.insert(ignore_permissions=True)
            state[v["key"]]["supplier"] = sup.name
            ok(f"Supplier created: {sup.name}")
        except Exception as e:
            fail(f"Supplier {v['name']}", e)
            state[v["key"]]["supplier"] = None
    frappe.db.commit()

    print("\n=== STEP 5: Customer ===")
    try:
        cust_group = frappe.db.get_value("Customer Group", {"customer_group_name": "Individual"}) or frappe.db.get_value("Customer Group", {}, "name")
        if not frappe.db.exists("Customer", "Cafeteria Walk-in Guest"):
            cust = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "Cafeteria Walk-in Guest",
                "customer_group": cust_group,
                "territory": frappe.db.get_value("Territory", {}, "name") or "All Territories",
            })
            cust.insert(ignore_permissions=True)
            ok(f"Customer created: {cust.name}")
        else:
            ok("Customer already exists: Cafeteria Walk-in Guest")
    except Exception as e:
        fail("Customer Cafeteria Walk-in Guest", e)
    frappe.db.commit()

    print("\n=== STEP 6: Item Group ===")
    try:
        if not frappe.db.exists("Item Group", "Cafeteria Food"):
            ig = frappe.get_doc({
                "doctype": "Item Group",
                "item_group_name": "Cafeteria Food",
                "parent_item_group": "All Item Groups",
            })
            ig.insert(ignore_permissions=True)
            ok("Item Group created: Cafeteria Food")
        else:
            ok("Item Group already exists: Cafeteria Food")
    except Exception as e:
        fail("Item Group Cafeteria Food", e)
    frappe.db.commit()

    print("\n=== STEP 7: Sales Taxes and Charges Template ===")
    tax_template_name = None
    try:
        tax_account = frappe.db.get_value(
            "Account",
            {"company": COMPANY, "account_type": "Tax", "is_group": 0},
            "name",
        )
        if tax_account and not frappe.db.exists("Sales Taxes and Charges Template", f"GST 5% - {ABBR}"):
            stt = frappe.get_doc({
                "doctype": "Sales Taxes and Charges Template",
                "title": "GST 5%",
                "company": COMPANY,
                "taxes": [{
                    "charge_type": "On Net Total",
                    "account_head": tax_account,
                    "rate": 5,
                    "description": "GST 5%",
                }],
            })
            stt.insert(ignore_permissions=True)
            tax_template_name = stt.name
            ok(f"Tax template created: {stt.name}")
        elif tax_account:
            tax_template_name = f"GST 5% - {ABBR}"
            ok("Tax template already exists")
        else:
            ok("No Tax-type account found on this company — skipped tax template (not blocking)")
    except Exception as e:
        fail("Sales Taxes and Charges Template", e)
    frappe.db.commit()

    print("\n=== STEP 8: Items ===")
    for it in ITEMS:
        try:
            if frappe.db.exists("Item", it["code"]):
                ok(f"Item exists: {it['code']}")
                continue
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": it["code"],
                "item_name": it["name"],
                "item_group": "Cafeteria Food",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "standard_rate": it["rate"],
            })
            item.insert(ignore_permissions=True)
            ok(f"Item created: {item.name}")
        except Exception as e:
            fail(f"Item {it['code']}", e)
    frappe.db.commit()

    print("\n=== STEP 9: Price Lists ===")
    for v in VENDORS:
        pl_name = f"{v['key']} Price List"
        try:
            if not frappe.db.exists("Price List", pl_name):
                pl = frappe.get_doc({
                    "doctype": "Price List",
                    "price_list_name": pl_name,
                    "currency": "INR",
                    "selling": 1,
                    "enabled": 1,
                })
                pl.insert(ignore_permissions=True)
                ok(f"Price List created: {pl.name}")
            else:
                ok(f"Price List already exists: {pl_name}")
            state[v["key"]]["price_list"] = pl_name
        except Exception as e:
            fail(f"Price List {pl_name}", e)
            state[v["key"]]["price_list"] = None
    frappe.db.commit()

    print("\n=== STEP 10: Item Prices ===")
    for it in ITEMS:
        pl_name = f"{it['vendor']} Price List"
        try:
            if not frappe.db.exists("Item Price", {"item_code": it["code"], "price_list": pl_name}):
                ip = frappe.get_doc({
                    "doctype": "Item Price",
                    "item_code": it["code"],
                    "price_list": pl_name,
                    "price_list_rate": it["rate"],
                    "selling": 1,
                    "currency": "INR",
                })
                ip.insert(ignore_permissions=True)
                ok(f"Item Price created: {it['code']} @ {pl_name} = {it['rate']}")
            else:
                ok(f"Item Price already exists: {it['code']} @ {pl_name}")
        except Exception as e:
            fail(f"Item Price {it['code']} @ {pl_name}", e)
    frappe.db.commit()

    print("\n=== STEP 11: Mode of Payment (UPI) ===")
    default_bank_account = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name")
    default_cash_account = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")
    fallback_account = default_bank_account or default_cash_account
    try:
        if not frappe.db.exists("Mode of Payment", "UPI"):
            mop = frappe.get_doc({
                "doctype": "Mode of Payment", "mode_of_payment": "UPI", "type": "Bank",
                "accounts": [{"company": COMPANY, "default_account": fallback_account}] if fallback_account else [],
            })
            mop.insert(ignore_permissions=True)
            ok("Mode of Payment created: UPI")
        else:
            ok("Mode of Payment already exists: UPI")
    except Exception as e:
        fail("Mode of Payment UPI", e)

    for mop_name in ["UPI", "Credit Card", "Cash"]:
        try:
            if not frappe.db.exists("Mode of Payment", mop_name):
                continue
            has_account = frappe.db.exists("Mode of Payment Account", {"parent": mop_name, "company": COMPANY})
            if has_account:
                ok(f"Mode of Payment '{mop_name}' already has a default account for {COMPANY}")
                continue
            if not fallback_account:
                fail(f"Mode of Payment account for {mop_name}", "no Bank/Cash account found on company")
                continue
            mop_doc = frappe.get_doc("Mode of Payment", mop_name)
            mop_doc.append("accounts", {"company": COMPANY, "default_account": fallback_account})
            mop_doc.save(ignore_permissions=True)
            ok(f"Default account set on Mode of Payment '{mop_name}': {fallback_account}")
        except Exception as e:
            fail(f"Default account for Mode of Payment {mop_name}", e)
    frappe.db.commit()

    print("\n=== STEP 12: Role (Corporate Management) ===")
    try:
        if not frappe.db.exists("Role", "Corporate Management"):
            role = frappe.get_doc({"doctype": "Role", "role_name": "Corporate Management", "desk_access": 1})
            role.insert(ignore_permissions=True)
            ok("Role created: Corporate Management")
        else:
            ok("Role already exists: Corporate Management")
    except Exception as e:
        fail("Role Corporate Management", e)
    frappe.db.commit()

    print("\n=== STEP 13: Users ===")
    for u in USERS:
        try:
            if frappe.db.exists("User", u["email"]):
                ok(f"User exists: {u['email']}")
                continue
            user = frappe.get_doc({
                "doctype": "User",
                "email": u["email"],
                "first_name": u["first"],
                "last_name": u["last"],
                "send_welcome_email": 0,
                "new_password": DEMO_PASSWORD,
                "roles": [{"role": r} for r in u["roles"]],
            })
            user.insert(ignore_permissions=True)
            ok(f"User created: {user.name}")
        except Exception as e:
            fail(f"User {u['email']}", e)
    frappe.db.commit()

    print("\n=== STEP 13b: Map users onto ury app's existing gate roles (URY Cashier / URY Manager) ===")
    print("NOTE: this site has a pre-existing 'ury' app whose has_permission hook blocks every")
    print("doctype for anyone without role System Manager / URY Manager / URY Captain / URY Cashier,")
    print("regardless of standard ERPNext role permissions. Layering these roles on top of our")
    print("Warehouse/Cost Center User Permissions lets the demo actually show data in the browser.")
    gate_role_map = {
        "cashier.southspice@campusbite.demo": "URY Cashier",
        "cashier.punjabtadka@campusbite.demo": "URY Cashier",
        "cashier.wokandroll@campusbite.demo": "URY Cashier",
        "cashier.beanthere@campusbite.demo": "URY Cashier",
        "manager.southspice@campusbite.demo": "URY Manager",
        "manager.punjabtadka@campusbite.demo": "URY Manager",
        "manager.wokandroll@campusbite.demo": "URY Manager",
        "manager.beanthere@campusbite.demo": "URY Manager",
        "ops.campusbite@campusbite.demo": "URY Manager",
    }
    for email, role in gate_role_map.items():
        try:
            udoc = frappe.get_doc("User", email)
            existing_roles = {r.role for r in udoc.roles}
            if role in existing_roles:
                ok(f"{email} already has gate role {role}")
                continue
            udoc.append("roles", {"role": role})
            udoc.save(ignore_permissions=True)
            ok(f"Added gate role {role} to {email}")
        except Exception as e:
            fail(f"Add gate role {role} to {email}", e)
    print("NOTE: admin.orion@techpark.demo (Corporate Management) is NOT given a URY role by design")
    print("(URY Manager/Cashier carry write access, which would break read-only). This means the")
    print("Corporate Management login will still be blocked by ury's gate in the live UI until that")
    print("app's permission.py allowed_roles list is updated to include 'Corporate Management' --")
    print("flagged as a Phase 2 follow-up rather than changed automatically.")
    frappe.db.commit()

    print("\n=== STEP 14: POS Profiles ===")
    default_cash_mop = "Cash" if frappe.db.exists("Mode of Payment", "Cash") else None
    for v in VENDORS:
        cc = state[v["key"]].get("cost_center")
        wh = state[v["key"]].get("warehouse")
        pl = state[v["key"]].get("price_list")
        profile_name = f"POS-{v['key']}"
        try:
            if frappe.db.exists("POS Profile", profile_name):
                state[v["key"]]["pos_profile"] = profile_name
                ok(f"POS Profile already exists: {profile_name}")
                continue
            payments = []
            if default_cash_mop:
                payments.append({"mode_of_payment": "Cash", "default": 1})
            if frappe.db.exists("Mode of Payment", "UPI"):
                payments.append({"mode_of_payment": "UPI"})
            if frappe.db.exists("Mode of Payment", "Credit Card"):
                payments.append({"mode_of_payment": "Credit Card"})

            write_off_account = frappe.db.get_value("Company", COMPANY, "write_off_account") or frappe.db.get_value(
                "Account", {"company": COMPANY, "account_type": "Expense Account", "is_group": 0}, "name"
            ) or frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name")

            pos = frappe.get_doc({
                "doctype": "POS Profile",
                "name": profile_name,
                "company": COMPANY,
                "warehouse": wh,
                "cost_center": cc,
                "customer": "Cafeteria Walk-in Guest",
                "currency": "INR",
                "selling_price_list": pl,
                "write_off_account": write_off_account,
                "write_off_cost_center": cc,
                "payments": payments,
                "applicable_for_users": [
                    {"user": u["email"]} for u in USERS if u["vendor"] == v["key"]
                ],
            })
            pos.insert(ignore_permissions=True)
            state[v["key"]]["pos_profile"] = pos.name
            ok(f"POS Profile created: {pos.name}")
        except Exception as e:
            fail(f"POS Profile {profile_name}", e)
            state[v["key"]]["pos_profile"] = None
    frappe.db.commit()

    print("\n=== STEP 15: User Permissions (vendor segregation) ===")
    for v in VENDORS:
        cc = state[v["key"]].get("cost_center")
        wh = state[v["key"]].get("warehouse")
        vendor_users = [u["email"] for u in USERS if u["vendor"] == v["key"]]
        for email in vendor_users:
            for doctype, value in [("Warehouse", wh), ("Cost Center", cc)]:
                if not value:
                    continue
                try:
                    exists = frappe.db.exists("User Permission", {
                        "user": email, "allow": doctype, "for_value": value
                    })
                    if exists:
                        ok(f"User Permission exists: {email} -> {doctype}={value}")
                        continue
                    up = frappe.get_doc({
                        "doctype": "User Permission",
                        "user": email,
                        "allow": doctype,
                        "for_value": value,
                        "apply_to_all_doctypes": 1,
                    })
                    up.insert(ignore_permissions=True)
                    ok(f"User Permission created: {email} -> {doctype}={value}")
                except Exception as e:
                    fail(f"User Permission {email} -> {doctype}={value}", e)
    frappe.db.commit()

    print("\n=== STEP 16: Role Permissions Manager (Corporate Management, read-only) ===")
    for dt in ["Sales Invoice", "Payment Entry", "Sales Order", "Item"]:
        try:
            exists = frappe.db.exists("Custom DocPerm", {"parent": dt, "role": "Corporate Management"})
            if exists:
                ok(f"Custom DocPerm exists: {dt} / Corporate Management")
                continue
            perm = frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": dt,
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": "Corporate Management",
                "read": 1,
                "report": 1,
                "write": 0,
                "create": 0,
                "delete": 0,
                "submit": 0,
                "cancel": 0,
                "amend": 0,
                "select": 1,
                "print": 1,
                "email": 1,
                "export": 1,
            })
            perm.insert(ignore_permissions=True)
            ok(f"Read-only permission added: {dt} / Corporate Management")
        except Exception as e:
            fail(f"Custom DocPerm {dt} / Corporate Management", e)
    frappe.clear_cache()
    frappe.db.commit()

    print("\n=== STEP 17: Sample POS Sales Invoices ===")
    sample_orders = {
        "SSK": [("SSK-001", 2, 150), ("SSK-002", 1, 90)],
        "PT": [("PT-001", 1, 220), ("PT-002", 1, 140)],
        "WR": [("WR-001", 1, 160), ("WR-002", 1, 150)],
        "BT": [("BT-001", 2, 80), ("BT-002", 1, 70)],
    }
    invoice_names = {}
    for v in VENDORS:
        key = v["key"]
        wh = state[key].get("warehouse")
        cc = state[key].get("cost_center")
        profile = state[key].get("pos_profile")
        if not (wh and cc and profile):
            fail(f"Sales Invoice for {v['name']}", "missing warehouse/cost center/pos profile")
            continue
        try:
            total = sum(q * r for _, q, r in sample_orders[key])
            si = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": "Cafeteria Walk-in Guest",
                "company": COMPANY,
                "due_date": nowdate(),
                "is_pos": 1,
                "pos_profile": profile,
                "set_warehouse": wh,
                "cost_center": cc,
                "selling_price_list": state[key].get("price_list"),
                "items": [
                    {"item_code": code, "qty": qty, "rate": rate, "warehouse": wh, "cost_center": cc}
                    for code, qty, rate in sample_orders[key]
                ],
                "payments": [{"mode_of_payment": "Cash", "amount": total}],
            })
            si.insert(ignore_permissions=True)
            si.submit()
            invoice_names[key] = si.name
            ok(f"Sales Invoice submitted for {v['name']}: {si.name} (Rs.{total})")
        except Exception as e:
            fail(f"Sales Invoice for {v['name']}", e)
    frappe.db.commit()
    state["_invoices"] = invoice_names

    print("\n=== STEP 18: Credit Note (refund) ===")
    try:
        ssk_invoice = invoice_names.get("SSK")
        if ssk_invoice:
            cn = frappe.get_doc({
                "doctype": "Sales Invoice",
                "customer": "Cafeteria Walk-in Guest",
                "company": COMPANY,
                "is_pos": 1,
                "pos_profile": state["SSK"].get("pos_profile"),
                "is_return": 1,
                "return_against": ssk_invoice,
                "set_warehouse": state["SSK"].get("warehouse"),
                "cost_center": state["SSK"].get("cost_center"),
                "items": [{
                    "item_code": "SSK-002",
                    "qty": -1,
                    "rate": 90,
                    "warehouse": state["SSK"].get("warehouse"),
                    "cost_center": state["SSK"].get("cost_center"),
                }],
                "payments": [{"mode_of_payment": "Cash", "amount": -90}],
            })
            cn.insert(ignore_permissions=True)
            cn.submit()
            ok(f"Credit Note submitted: {cn.name} against {ssk_invoice}")
        else:
            fail("Credit Note", "South Spice Kitchen invoice not available")
    except Exception as e:
        fail("Credit Note", e)
    frappe.db.commit()

    print("\n=== STEP 18b: Cleanup stray Payment Entry drafts from earlier partial runs ===")
    try:
        stray = frappe.get_all(
            "Payment Entry",
            filters={"reference_no": ["like", "SETTLE-AUG-2026-%"], "docstatus": 0},
        )
        for row in stray:
            frappe.delete_doc("Payment Entry", row.name, ignore_permissions=True, force=True)
            ok(f"Deleted stray draft Payment Entry: {row.name}")
        frappe.db.commit()
    except Exception as e:
        fail("Cleanup stray Payment Entry drafts", e)

    print("\n=== STEP 19: Payment Entries (Vendor Settlement Payouts) ===")
    payable_account = frappe.db.get_value("Company", COMPANY, "default_payable_account")
    bank_account = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name")
    cash_account = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Cash", "is_group": 0}, "name")
    paid_from = bank_account or cash_account
    settlements = {
        "SSK": 156730,
        "PT": 186098,
        "WR": 124960,
        "BT": 119100,
    }
    for v in VENDORS:
        key = v["key"]
        supplier = state[key].get("supplier")
        amount = settlements[key]
        if not (supplier and paid_from and payable_account):
            fail(f"Payment Entry for {v['name']}", "missing supplier/paid_from/payable account")
            continue
        ref_no = f"SETTLE-AUG-2026-{key}"
        if frappe.db.exists("Payment Entry", {"reference_no": ref_no, "docstatus": ["!=", 2]}):
            ok(f"Payment Entry already exists for {v['name']} (ref {ref_no})")
            continue
        try:
            pe = frappe.get_doc({
                "doctype": "Payment Entry",
                "payment_type": "Pay",
                "party_type": "Supplier",
                "party": supplier,
                "company": COMPANY,
                "paid_amount": amount,
                "received_amount": amount,
                "paid_from": paid_from,
                "paid_to": payable_account,
                "reference_no": f"SETTLE-AUG-2026-{key}",
                "reference_date": nowdate(),
            })
            pe.insert(ignore_permissions=True)
            ok(f"Payment Entry created (Draft) for {v['name']}: {pe.name} (Rs.{amount})")
        except Exception as e:
            fail(f"Payment Entry for {v['name']}", e)
    frappe.db.commit()

    print("\n=== SUMMARY ===")
    for v in VENDORS:
        print(f"{v['name']}: {state[v['key']]}")
    print("Invoices:", invoice_names)
    print("=== DONE ===")
