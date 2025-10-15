import frappe
from frappe.utils import today

def after_install():
	"""Setup SMS Trigger app after installation"""
	try:
		create_custom_fields()
		setup_default_sms_rules()
		setup_workspace()
		frappe.db.commit()
		print("SMS Trigger app installed successfully!")
	except Exception as e:
		frappe.log_error(f"Error during SMS Trigger installation: {str(e)}", "SMS Trigger Install Error")

def create_custom_fields():
	"""Create custom fields for SMS integration"""
	try:
		# Add SMS field to Customer
		if not frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "sms_enabled"}):
			frappe.get_doc({
				"doctype": "Custom Field",
				"dt": "Customer",
				"fieldname": "sms_enabled",
				"label": "SMS Enabled",
				"fieldtype": "Check",
				"default": "1",
				"insert_after": "mobile_no",
				"description": "Enable/disable SMS notifications for this customer"
			}).insert(ignore_permissions=True)
		
		# Add date of birth field if not exists
		if not frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "date_of_birth"}):
			frappe.get_doc({
				"doctype": "Custom Field",
				"dt": "Customer",
				"fieldname": "date_of_birth",
				"label": "Date of Birth",
				"fieldtype": "Date",
				"insert_after": "sms_enabled",
				"description": "Customer's date of birth for birthday SMS triggers"
			}).insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(f"Error creating custom fields: {str(e)}", "SMS Install Error")

def setup_default_sms_rules():
	"""Setup default SMS trigger rules"""
	default_rules = [
		{
			"rule_name": "Invoice Due Reminder",
			"trigger_type": "Invoice Due",
			"frequency": "Daily",
			"days_interval": 7,
			"message_template": "Dear {{ customer_name }}, your invoice {{ invoice_no }} for {{ amount }} is overdue. Please make payment at your earliest convenience.",
			"is_active": 1
		},
		{
			"rule_name": "Birthday Wishes",
			"trigger_type": "Birthday",
			"frequency": "Daily",
			"message_template": "Happy Birthday {{ customer_name }}! Wishing you a wonderful day filled with joy and happiness. Thank you for being our valued customer!",
			"is_active": 1
		},
		{
			"rule_name": "Inactive Customer Follow-up",
			"trigger_type": "Inactive Customer",
			"frequency": "Monthly",
			"days_interval": 90,
			"message_template": "Hi {{ customer_name }}, we miss you! It's been a while since your last purchase. Check out our latest offers and come back soon!",
			"is_active": 0
		}
	]
	
	for rule_data in default_rules:
		try:
			if not frappe.db.exists("SMS Trigger Rule", {"rule_name": rule_data["rule_name"]}):
				doc = frappe.get_doc({
					"doctype": "SMS Trigger Rule",
					**rule_data
				})
				doc.insert(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Error creating default rule {rule_data['rule_name']}: {str(e)}", "SMS Install Error")

def setup_workspace():
	"""Setup SMS workspace if it doesn't exist"""
	try:
		if not frappe.db.exists("Workspace", "SMS"):
			workspace = frappe.get_doc({
				"doctype": "Workspace",
				"title": "SMS",
				"name": "SMS",
				"icon": "message-square",
				"indicator_color": "blue",
				"is_standard": 1,
				"module": "SMS Trigger"
			})
			workspace.insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(f"Error creating workspace: {str(e)}", "SMS Install Error")