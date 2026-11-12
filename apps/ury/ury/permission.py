import frappe

def check_app_permission():
    if frappe.session.user == "Administrator":
        return True
    
    user_roles = frappe.get_roles(frappe.session.user)
    
    allowed_roles = [
        "System Manager",
        "URY Manager", 
        "URY Captain",
        "URY Cashier"
    ]
    
    for role in allowed_roles:
        if role in user_roles:
            return True
    
    return False
