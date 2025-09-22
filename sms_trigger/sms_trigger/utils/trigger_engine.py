import frappe
from frappe.utils import add_days, getdate, now_datetime, get_datetime
import json

def process_sms_triggers():
	"""Main function to process all SMS trigger rules"""
	rules = frappe.get_all("SMS Trigger Rule", 
		filters={"is_active": 1}, 
		fields=["name", "trigger_type", "conditions", "message_template", "days_interval"]
	)
	
	for rule in rules:
		try:
			process_trigger_rule(rule)
		except Exception as e:
			frappe.log_error(f"Error processing rule {rule.name}: {str(e)}", "SMS Trigger Error")

def process_trigger_rule(rule):
	"""Process individual trigger rule"""
	trigger_type = rule.trigger_type
	
	if trigger_type == "Invoice Due":
		process_invoice_due(rule)
	elif trigger_type == "Birthday":
		process_birthday(rule)
	elif trigger_type == "Inactive Customer":
		process_inactive_customer(rule)
	elif trigger_type == "Repurchase Promotion":
		process_repurchase_promotion(rule)
	elif trigger_type == "Customer Type":
		process_customer_type(rule)
	elif trigger_type == "Customer Group":
		process_customer_group(rule)

def process_invoice_due(rule):
	"""Process overdue invoices"""
	days_overdue = rule.days_interval or 7
	due_date = add_days(getdate(), -days_overdue)
	
	invoices = frappe.db.sql("""
		SELECT si.customer, si.name, si.due_date, si.outstanding_amount
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 
		AND si.outstanding_amount > 0
		AND si.due_date <= %s
	""", (due_date,), as_dict=True)
	
	for invoice in invoices:
		# Check if SMS already scheduled
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": invoice.customer,
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice.name,
			"trigger_type": "Invoice Due"
		})
		
		if not existing:
			create_scheduled_sms(
				customer=invoice.customer,
				message=rule.message_template.format(
					customer_name=frappe.get_value("Customer", invoice.customer, "customer_name"),
					invoice_no=invoice.name,
					amount=invoice.outstanding_amount
				),
				trigger_type="Invoice Due",
				reference_doctype="Sales Invoice",
				reference_name=invoice.name
			)

def process_birthday(rule):
	"""Process customer birthdays"""
	today = getdate()
	
	customers = frappe.db.sql("""
		SELECT name, customer_name, mobile_no
		FROM `tabCustomer`
		WHERE DATE_FORMAT(date_of_birth, '%%m-%%d') = %s
		AND mobile_no IS NOT NULL
	""", (today.strftime('%m-%d'),), as_dict=True)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Birthday",
			"scheduled_datetime": [">=", today]
		})
		
		if not existing:
			create_scheduled_sms(
				customer=customer.name,
				message=rule.message_template.format(
					customer_name=customer.customer_name
				),
				trigger_type="Birthday"
			)

def process_inactive_customer(rule):
	"""Process inactive customers"""
	days_inactive = rule.days_interval or 90
	cutoff_date = add_days(getdate(), -days_inactive)
	
	customers = frappe.db.sql("""
		SELECT DISTINCT c.name, c.customer_name, c.mobile_no
		FROM `tabCustomer` c
		LEFT JOIN `tabSales Invoice` si ON si.customer = c.name
		WHERE c.mobile_no IS NOT NULL
		AND (si.posting_date IS NULL OR si.posting_date < %s)
		GROUP BY c.name
	""", (cutoff_date,), as_dict=True)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Inactive Customer",
			"scheduled_datetime": [">=", add_days(getdate(), -30)]
		})
		
		if not existing:
			create_scheduled_sms(
				customer=customer.name,
				message=rule.message_template.format(
					customer_name=customer.customer_name
				),
				trigger_type="Inactive Customer"
			)

def process_repurchase_promotion(rule):
	"""Process repurchase promotion"""
	conditions = json.loads(rule.conditions or "{}")
	item_code = conditions.get("item_code")
	days_ago = rule.days_interval or 30
	
	if not item_code:
		return
	
	cutoff_date = add_days(getdate(), -days_ago)
	
	customers = frappe.db.sql("""
		SELECT DISTINCT si.customer, c.customer_name, c.mobile_no
		FROM `tabSales Invoice` si
		JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		JOIN `tabCustomer` c ON c.name = si.customer
		WHERE sii.item_code = %s
		AND si.posting_date >= %s
		AND c.mobile_no IS NOT NULL
	""", (item_code, cutoff_date), as_dict=True)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.customer,
			"trigger_type": "Repurchase Promotion",
			"scheduled_datetime": [">=", add_days(getdate(), -7)]
		})
		
		if not existing:
			create_scheduled_sms(
				customer=customer.customer,
				message=rule.message_template.format(
					customer_name=customer.customer_name,
					item_code=item_code
				),
				trigger_type="Repurchase Promotion"
			)

def process_customer_type(rule):
	"""Process customer type based triggers"""
	conditions = json.loads(rule.conditions or "{}")
	customer_type = conditions.get("customer_type")
	
	if not customer_type:
		return
	
	customers = frappe.get_all("Customer", 
		filters={"customer_type": customer_type, "mobile_no": ["!=", ""]},
		fields=["name", "customer_name", "mobile_no"]
	)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Customer Type",
			"scheduled_datetime": [">=", add_days(getdate(), -30)]
		})
		
		if not existing:
			create_scheduled_sms(
				customer=customer.name,
				message=rule.message_template.format(
					customer_name=customer.customer_name
				),
				trigger_type="Customer Type"
			)

def process_customer_group(rule):
	"""Process customer group based triggers"""
	conditions = json.loads(rule.conditions or "{}")
	customer_group = conditions.get("customer_group")
	
	if not customer_group:
		return
	
	customers = frappe.get_all("Customer", 
		filters={"customer_group": customer_group, "mobile_no": ["!=", ""]},
		fields=["name", "customer_name", "mobile_no"]
	)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Customer Group",
			"scheduled_datetime": [">=", add_days(getdate(), -30)]
		})
		
		if not existing:
			create_scheduled_sms(
				customer=customer.name,
				message=rule.message_template.format(
					customer_name=customer.customer_name
				),
				trigger_type="Customer Group"
			)

def create_scheduled_sms(customer, message, trigger_type, reference_doctype=None, reference_name=None):
	"""Create scheduled SMS entry"""
	doc = frappe.get_doc({
		"doctype": "Scheduled SMS",
		"customer": customer,
		"message": message,
		"trigger_type": trigger_type,
		"scheduled_datetime": now_datetime(),
		"reference_doctype": reference_doctype,
		"reference_name": reference_name
	})
	doc.insert()
	return doc

def send_pending_sms():
	"""Send all pending SMS"""
	pending_sms = frappe.get_all("Scheduled SMS",
		filters={
			"status": "Draft",
			"scheduled_datetime": ["<=", now_datetime()]
		},
		fields=["name"]
	)
	
	for sms in pending_sms:
		doc = frappe.get_doc("Scheduled SMS", sms.name)
		doc.send_sms()