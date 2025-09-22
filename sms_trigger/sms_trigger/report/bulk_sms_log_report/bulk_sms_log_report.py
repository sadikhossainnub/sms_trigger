import frappe

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def get_columns():
	return [
		{"label": "Campaign", "fieldname": "campaign_name", "fieldtype": "Data", "width": 150},
		{"label": "Customer", "fieldname": "customer_name", "fieldtype": "Data", "width": 150},
		{"label": "Mobile No", "fieldname": "mobile_no", "fieldtype": "Data", "width": 120},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 80},
		{"label": "Sent Date", "fieldname": "sent_datetime", "fieldtype": "Datetime", "width": 150},
		{"label": "Message", "fieldname": "message", "fieldtype": "Text", "width": 200},
		{"label": "Error", "fieldname": "error_message", "fieldtype": "Text", "width": 150}
	]

def get_data(filters):
	conditions = []
	values = []
	
	if filters.get("campaign_name"):
		conditions.append("campaign_name LIKE %s")
		values.append(f"%{filters.get('campaign_name')}%")
	
	if filters.get("status"):
		conditions.append("status = %s")
		values.append(filters.get("status"))
	
	if filters.get("from_date"):
		conditions.append("sent_datetime >= %s")
		values.append(filters.get("from_date"))
	
	if filters.get("to_date"):
		conditions.append("sent_datetime <= %s")
		values.append(filters.get("to_date"))
	
	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	return frappe.db.sql(f"""
		SELECT campaign_name, customer_name, mobile_no, status, 
			   sent_datetime, message, error_message
		FROM `tabBulk SMS Log`
		WHERE {where_clause}
		ORDER BY sent_datetime DESC
	""", values, as_dict=True)