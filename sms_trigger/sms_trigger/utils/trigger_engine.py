import frappe
from frappe.utils import add_days, getdate, now_datetime, get_datetime, cstr
import json

def process_sms_triggers():
	"""Main function to process all SMS trigger rules"""
	try:
		rules = frappe.get_all("SMS Trigger Rule", 
			filters={"is_active": 1, "docstatus": 1}, 
			fields=["name", "trigger_type", "conditions", "message_template", "days_interval", "frequency"]
		)
		
		for rule_data in rules:
			try:
				rule = frappe.get_doc("SMS Trigger Rule", rule_data.name)
				if rule.can_execute():
					process_trigger_rule(rule)
					rule.mark_executed()
			except Exception as e:
				frappe.log_error(f"Error processing rule {rule_data.name}: {str(e)}", "SMS Trigger Error")
	except Exception as e:
		frappe.log_error(f"Error in process_sms_triggers: {str(e)}", "SMS Trigger Error")

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
		SELECT si.customer, si.name, si.due_date, si.outstanding_amount, c.mobile_no
		FROM `tabSales Invoice` si
		JOIN `tabCustomer` c ON c.name = si.customer
		WHERE si.docstatus = 1 
		AND si.outstanding_amount > 0
		AND si.due_date <= %s
		AND c.mobile_no IS NOT NULL
		AND c.mobile_no != ''
		AND IFNULL(c.sms_enabled, 1) = 1
	""", (due_date,), as_dict=True)
	
	for invoice in invoices:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": invoice.customer,
			"reference_doctype": "Sales Invoice",
			"reference_name": invoice.name,
			"trigger_type": "Invoice Due"
		})
		
		if not existing:
			try:
				customer_name = frappe.get_value("Customer", invoice.customer, "customer_name")
				context = {
					"customer_name": customer_name,
					"invoice_no": invoice.name,
					"amount": invoice.outstanding_amount,
					"today": frappe.utils.today(),
				}
				message = frappe.render_template(rule.message_template, context)
				create_scheduled_sms(
					customer=invoice.customer,
					message=message,
					trigger_type="Invoice Due",
					reference_doctype="Sales Invoice",
					reference_name=invoice.name
				)
			except Exception as e:
				frappe.log_error(f"Error formatting invoice due message for {invoice.name}: {str(e)}", "SMS Trigger Error")

def process_birthday(rule):
	"""Process customer birthdays"""
	today = getdate()
	
	customers = frappe.db.sql("""
		SELECT name, customer_name, mobile_no
		FROM `tabCustomer`
		WHERE DATE_FORMAT(date_of_birth, '%%m-%%d') = %s
		AND mobile_no IS NOT NULL
		AND mobile_no != ''
		AND IFNULL(sms_enabled, 1) = 1
	""", (today.strftime('%m-%d'),), as_dict=True)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Birthday",
			"scheduled_datetime": [">=", today]
		})
		
		if not existing:
			try:
				context = {
					"customer_name": customer.customer_name,
					"today": frappe.utils.today(),
				}
				message = frappe.render_template(rule.message_template, context)
				create_scheduled_sms(
					customer=customer.name,
					message=message,
					trigger_type="Birthday"
				)
			except Exception as e:
				frappe.log_error(f"Error formatting birthday message for customer {customer.name}: {str(e)}", "SMS Trigger Error")

def process_inactive_customer(rule):
	"""Process inactive customers"""
	days_inactive = rule.days_interval or 90
	cutoff_date = add_days(getdate(), -days_inactive)
	
	customers = frappe.db.sql("""
		SELECT DISTINCT c.name, c.customer_name, c.mobile_no
		FROM `tabCustomer` c
		WHERE c.mobile_no IS NOT NULL
		AND c.mobile_no != ''
		AND IFNULL(c.sms_enabled, 1) = 1
		AND NOT EXISTS (
			SELECT 1
			FROM `tabSales Invoice` si
			WHERE si.customer = c.name
			AND si.docstatus = 1
			AND si.posting_date >= %s
		)
	""", (cutoff_date,), as_dict=True)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Inactive Customer",
			"scheduled_datetime": [">=", add_days(getdate(), -30)]
		})
		
		if not existing:
			try:
				context = {
					"customer_name": customer.customer_name,
					"today": frappe.utils.today(),
				}
				message = frappe.render_template(rule.message_template, context)
				create_scheduled_sms(
					customer=customer.name,
					message=message,
					trigger_type="Inactive Customer"
				)
			except Exception as e:
				frappe.log_error(f"Error formatting inactive customer message for {customer.name}: {str(e)}", "SMS Trigger Error")

def process_repurchase_promotion(rule):
	"""Process repurchase promotion"""
	try:
		conditions = json.loads(rule.conditions or "{}")
		if not isinstance(conditions, dict):
			frappe.log_error(f"Conditions for rule {rule.name} must be a JSON object, got {type(conditions)}", "SMS Trigger Error")
			return
	except json.JSONDecodeError:
		frappe.log_error(f"Invalid JSON format in conditions for rule {rule.name}", "SMS Trigger Error")
		return
	
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
		AND c.mobile_no != ''
		AND IFNULL(c.sms_enabled, 1) = 1
	""", (item_code, cutoff_date), as_dict=True)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.customer,
			"trigger_type": "Repurchase Promotion",
			"scheduled_datetime": [">=", add_days(getdate(), -7)]
		})
		
		if not existing:
			try:
				context = {
					"customer_name": customer.customer_name,
					"item_code": item_code,
					"today": frappe.utils.today(),
				}
				message = frappe.render_template(rule.message_template, context)
				create_scheduled_sms(
					customer=customer.customer,
					message=message,
					trigger_type="Repurchase Promotion"
				)
			except Exception as e:
				frappe.log_error(f"Error formatting message for customer {customer.customer}: {str(e)}", "SMS Trigger Error")

def process_customer_type(rule):
	"""Process customer type based triggers"""
	try:
		conditions = json.loads(rule.conditions or "{}")
		if not isinstance(conditions, dict):
			frappe.log_error(f"Conditions for rule {rule.name} must be a JSON object, got {type(conditions)}", "SMS Trigger Error")
			return
	except json.JSONDecodeError:
		frappe.log_error(f"Invalid JSON format in conditions for rule {rule.name}", "SMS Trigger Error")
		return
	
	customer_type = conditions.get("customer_type")
	if not customer_type:
		return
	
	filters = {"customer_type": customer_type, "mobile_no": ["!=", ""], "sms_enabled": ["!=", 0]}
	
	for key, value in conditions.items():
		if key != "customer_type" and frappe.get_meta("Customer").has_field(key):
			filters[key] = value
	
	customers = frappe.get_all("Customer", 
		filters=filters,
		fields=["name", "customer_name", "mobile_no"]
	)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Customer Type",
			"scheduled_datetime": [">=", add_days(getdate(), -30)]
		})
		
		if not existing:
			try:
				context = {
					"customer_name": customer.customer_name,
					"today": frappe.utils.today(),
				}
				message = frappe.render_template(rule.message_template, context)
				create_scheduled_sms(
					customer=customer.name,
					message=message,
					trigger_type="Customer Type"
				)
			except Exception as e:
				frappe.log_error(f"Error formatting message for customer {customer.name}: {str(e)}", "SMS Trigger Error")

def process_customer_group(rule):
	"""Process customer group based triggers"""
	try:
		conditions = json.loads(rule.conditions or "{}")
		if not isinstance(conditions, dict):
			frappe.log_error(f"Conditions for rule {rule.name} must be a JSON object, got {type(conditions)}", "SMS Trigger Error")
			return
	except json.JSONDecodeError:
		frappe.log_error(f"Invalid JSON format in conditions for rule {rule.name}", "SMS Trigger Error")
		return
	
	customer_group = conditions.get("customer_group")
	if not customer_group:
		return
	
	filters = {"customer_group": customer_group, "mobile_no": ["!=", ""], "sms_enabled": ["!=", 0]}
	
	for key, value in conditions.items():
		if key != "customer_group" and frappe.get_meta("Customer").has_field(key):
			filters[key] = value
	
	customers = frappe.get_all("Customer", 
		filters=filters,
		fields=["name", "customer_name", "mobile_no"]
	)
	
	for customer in customers:
		existing = frappe.db.exists("Scheduled SMS", {
			"customer": customer.name,
			"trigger_type": "Customer Group",
			"scheduled_datetime": [">=", add_days(getdate(), -30)]
		})
		
		if not existing:
			try:
				context = {
					"customer_name": customer.customer_name,
					"today": frappe.utils.today(),
				}
				message = frappe.render_template(rule.message_template, context)
				create_scheduled_sms(
					customer=customer.name,
					message=message,
					trigger_type="Customer Group"
				)
			except Exception as e:
				frappe.log_error(f"Error formatting message for customer {customer.name}: {str(e)}", "SMS Trigger Error")

def create_scheduled_sms(customer, message, trigger_type, reference_doctype=None, reference_name=None, scheduled_datetime=None):
	"""Create scheduled SMS entry"""
	try:
		if not scheduled_datetime:
			scheduled_datetime = now_datetime()
		
		mobile_no = frappe.get_value("Customer", customer, "mobile_no")
		if not mobile_no:
			frappe.log_error(f"Customer {customer} has no mobile number", "SMS Trigger Error")
			return None
		
		doc = frappe.get_doc({
			"doctype": "Scheduled SMS",
			"customer": customer,
			"mobile_no": mobile_no,
			"message": message,
			"trigger_type": trigger_type,
			"scheduled_datetime": scheduled_datetime,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name
		})
		doc.insert(ignore_permissions=True)
		doc.submit()
		frappe.db.commit()
		return doc
	except Exception as e:
		frappe.log_error(f"Error creating scheduled SMS for customer {customer}: {str(e)}", "SMS Trigger Error")
		return None

def send_pending_sms():
	"""Send pending SMS messages"""
	try:
		pending_sms = frappe.get_all("Scheduled SMS", 
			filters={
				"status": "Draft",
				"docstatus": 1,
				"scheduled_datetime": ["<=", now_datetime()]
			},
			fields=["name"],
			limit=100
		)
		
		for sms_data in pending_sms:
			try:
				sms = frappe.get_doc("Scheduled SMS", sms_data.name)
				result = sms.send_sms()
				
				# Reload and commit to ensure status is saved
				sms.reload()
				frappe.db.commit()
				
				if result.get("success"):
					frappe.log_info(f"SMS {sms_data.name} sent successfully", "SMS Send")
				else:
					frappe.log_error(f"SMS {sms_data.name} failed: {result.get('error')}", "SMS Send Error")
					
			except Exception as e:
				frappe.log_error(f"Error sending SMS {sms_data.name}: {str(e)}", "SMS Send Error")
				# Try to mark as failed
				try:
					sms = frappe.get_doc("Scheduled SMS", sms_data.name)
					sms.status = "Failed"
					sms.error_message = str(e)
					sms.save(ignore_permissions=True, ignore_version=True)
					frappe.db.commit()
				except:
					pass
					
	except Exception as e:
		frappe.log_error(f"Error in send_pending_sms: {str(e)}", "SMS Send Error")

def cleanup_old_logs():
	"""Cleanup old SMS logs to prevent database bloat"""
	try:
		cutoff_date = add_days(getdate(), -90)
		frappe.db.sql("""
			DELETE FROM `tabScheduled SMS` 
			WHERE status IN ('Sent', 'Failed') 
			AND DATE(scheduled_datetime) < %s
		""", (cutoff_date,))
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error in cleanup_old_logs: {str(e)}", "SMS Cleanup Error")