import frappe
from frappe.utils import getdate

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 150},
		{"label": "Mobile No", "fieldname": "mobile_no", "fieldtype": "Data", "width": 120},
		{"label": "Trigger Type", "fieldname": "trigger_type", "fieldtype": "Data", "width": 120},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": "Scheduled Date", "fieldname": "scheduled_datetime", "fieldtype": "Datetime", "width": 150},
		{"label": "Sent Date", "fieldname": "sent_datetime", "fieldtype": "Datetime", "width": 150},
		{"label": "Message", "fieldname": "message", "fieldtype": "Text", "width": 200},
		{"label": "Error", "fieldname": "error_message", "fieldtype": "Text", "width": 150}
	]

def get_data(filters):
	conditions = []
	values = []
	
	if filters.get("customer"):
		conditions.append("customer = %s")
		values.append(filters.get("customer"))
	
	if filters.get("status"):
		conditions.append("status = %s")
		values.append(filters.get("status"))
	
	if filters.get("trigger_type"):
		conditions.append("trigger_type = %s")
		values.append(filters.get("trigger_type"))
	
	if filters.get("from_date"):
		conditions.append("scheduled_datetime >= %s")
		values.append(filters.get("from_date"))
	
	if filters.get("to_date"):
		conditions.append("scheduled_datetime <= %s")
		values.append(filters.get("to_date"))
	
	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	return frappe.db.sql(f"""
		SELECT customer, mobile_no, trigger_type, status, 
			   scheduled_datetime, sent_datetime, message, error_message
		FROM `tabScheduled SMS`
		WHERE {where_clause}
		ORDER BY scheduled_datetime DESC
	""", values, as_dict=True)