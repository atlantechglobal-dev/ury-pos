import frappe
from frappe import _
from frappe.utils import cint
from frappe.utils.print_format import print_by_server

KOT_REPRINT_ALLOWED_ROLES = {"System Manager", "URY Cashier", "URY Manager"}


@frappe.whitelist()
def reprint_kot(invoice_number):
    # KOT Reprint is an override action — once a KOT is punched, a Captain
    # must get it right or the order gets cancelled, not reprinted. Only
    # Admin/Cashier/Manager can reprint. Checked outside the try/except below
    # so the specific message isn't swallowed by its generic error handler.
    if frappe.session.user != "Administrator" and not (KOT_REPRINT_ALLOWED_ROLES & set(frappe.get_roles())):
        frappe.throw(_("Only Cashier, Manager or Administrator can reprint a KOT"), frappe.PermissionError)

    try:
        pos_profile, restaurant_table, order_type = frappe.db.get_value(
            "POS Invoice", invoice_number, ["pos_profile", "restaurant_table","order_type"]
        )
        if not pos_profile:
            frappe.throw(f"POS Profile not found for Invoice {invoice_number}.")

        enable_kot_reprint, kot_print_format, table_order_printer, parcel_order_printer = frappe.db.get_value(
            "POS Profile", pos_profile,
            ["custom_enable_kot_reprint", "custom_reprint_kot_format", "custom_table_order_printer", "custom_parcel_order_printer"]
        )


        if not cint(enable_kot_reprint):
            frappe.throw("KOT Reprint is disabled in POS Profile.")

        if not kot_print_format:
            frappe.throw("No KOT Reprint Print Format is set in POS Profile.")

        printer = table_order_printer if order_type == "Dine In" else parcel_order_printer

        if not printer:
            frappe.throw("No printer is assigned for reprinting KOT.")


        print_kot(printer, invoice_number, kot_print_format)


        return "Success"

    except Exception as e:
        error_message = f"KOT Reprint Error for Invoice {invoice_number}: {str(e)}"
        frappe.log_error(error_message, "KOT Reprint Error")
        frappe.throw("An unexpected error occurred while reprinting KOT. Please check logs.")


def print_kot(printer,docname, kot_print_format):
    try:
        print_by_server("POS Invoice",docname, printer, kot_print_format)
    except Exception as e:
        frappe.log_error(f"KOT Reprint Error: {e}")
