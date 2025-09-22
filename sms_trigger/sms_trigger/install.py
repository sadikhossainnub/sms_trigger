import frappe

def after_install():
	"""Setup SMS Trigger app after installation"""
	create_custom_fields()
	setup_notification_templates()

def create_custom_fields():
	"""Create custom fields for SMS integration"""
	# Add SMS field to Customer
	if not frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "sms_enabled"}):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Customer",
			"fieldname": "sms_enabled",
			"label": "SMS Enabled",
			"fieldtype": "Check",
			"default": "1",
			"insert_after": "mobile_no"
		}).insert()

def setup_notification_templates():
	"""Setup default notification templates"""
	templates = [
		{
			"name": "Invoice Due SMS",
			"subject": "Invoice Due Reminder",
			"document_type": "Sales Invoice",
			"event": "Days After",
			"date_changed": "due_date",
			"days_in_advance": -7,
			"condition": "doc.outstanding_amount > 0",
			"message": "Dear {{ doc.customer_name }}, your invoice {{ doc.name }} for {{ doc.grand_total }} is overdue. Please make payment."
		}
	]
	
	for template in templates:
		if not frappe.db.exists("Notification", template["name"]):
			doc = frappe.get_doc({
				"doctype": "Notification",
				**template,
				"enabled": 1,
				"channel": "SMS"
			})
			doc.insert()