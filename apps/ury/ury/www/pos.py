import json
import re
import frappe
import frappe.sessions
from frappe import _
from frappe.utils.telemetry import capture

no_cache = 1

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")

def get_context(context):
    # Permission Check
    if frappe.session.user == "Guest":
        frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
    
    user_roles = frappe.get_roles(frappe.session.user)
    allowed_roles = ["System Manager", "URY Manager", "URY Captain", "URY Cashier", "Administrator"]
    
    if not any(role in user_roles for role in allowed_roles):
        frappe.throw(_("You do not have permission to access URY POS"), frappe.PermissionError)

    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()
    
    try:
        boot = frappe.sessions.get()
    except Exception as e:
        raise frappe.SessionBootFailed from e

    if "server_script_enabled" in frappe.conf:
        enabled = frappe.conf.server_script_enabled
    else:
        enabled = True
    boot["server_script_enabled"] = enabled

    boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))
    boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)
    boot_json = json.dumps(boot_json)

    context.update(
        {"build_version": frappe.utils.get_build_version(), "boot": boot_json, "csrf_token": csrf_token}
    )
    return context
