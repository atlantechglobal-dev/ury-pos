import frappe


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Captain", "fieldname": "captain", "fieldtype": "Data", "width": 180},
        {"label": "Table", "fieldname": "restaurant_table", "fieldtype": "Data", "width": 100},
        {"label": "Invoice", "fieldname": "name", "fieldtype": "Link", "options": "POS Invoice", "width": 150},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
        {"label": "Grand Total", "fieldname": "grand_total", "fieldtype": "Currency", "width": 120},
        {"label": "Commission", "fieldname": "commission", "fieldtype": "Currency", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]


def get_data(filters):
    conditions = ["b.docstatus = 1", "b.posting_date BETWEEN %(start_date)s AND %(end_date)s"]
    values = {
        "start_date": filters.get("start_date"),
        "end_date": filters.get("end_date"),
    }

    if filters.get("branch"):
        conditions.append("b.branch = %(branch)s")
        values["branch"] = filters.get("branch")

    if filters.get("waiter"):
        conditions.append("b.waiter = %(waiter)s")
        values["waiter"] = filters.get("waiter")

    query = f"""
        SELECT
            b.posting_date,
            u.full_name AS captain,
            b.restaurant_table,
            b.name,
            b.customer,
            b.grand_total,
            b.status,
            COALESCE(SUM(
                CASE
                    WHEN i.custom_commission_type = 'Percentage'
                        THEN pi.amount * (i.custom_commission_value / 100)
                    WHEN i.custom_commission_type = 'Amount'
                        THEN i.custom_commission_value * pi.qty
                    ELSE 0
                END
            ), 0) AS commission
        FROM `tabPOS Invoice` b
        LEFT JOIN `tabUser` u ON u.name = b.waiter
        LEFT JOIN `tabPOS Invoice Item` pi ON pi.parent = b.name
        LEFT JOIN `tabItem` i ON i.name = pi.item_code
        WHERE {' AND '.join(conditions)}
        GROUP BY b.name, b.posting_date, u.full_name, b.restaurant_table,
                 b.customer, b.grand_total, b.status, b.posting_time
        ORDER BY b.posting_date DESC, b.posting_time DESC
    """

    return frappe.db.sql(query, values, as_dict=True)
