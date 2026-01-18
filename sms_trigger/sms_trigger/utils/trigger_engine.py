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

def get_filters_from_rule(rule):
	"""Build filters from rule conditions (JSON or Table)"""
	filters = []
	
	# Handle Visual Builder (Table)
	if not rule.use_json and rule.condition_table:
		for row in rule.condition_table:
			filters.append([row.field, row.operator, row.value])
			
	# Handle JSON (Advanced or Legacy)
	elif rule.conditions:
		try:
			conditions = json.loads(rule.conditions)
			if isinstance(conditions, dict):
				# Convert simple dict to filter list
				for key, value in conditions.items():
					# Skip special keys handled separately (like customer_type in its specific handler)
					if key in ["customer_type", "customer_group", "item_code"]:
						continue
					filters.append([key, "=", value])
		except:
			pass
			
	return filters

def process_customer_type(rule):
	"""Process customer type based triggers"""
	# Get base filters from rule
	filters = get_filters_from_rule(rule)
	
	# Add mandatory filters
	filters.append(["mobile_no", "!=", ""])
	filters.append(["sms_enabled", "!=", 0])
	
	# Handle special 'customer_type' field from JSON or Table
	# If using JSON, we need to extract customer_type specifically if it exists there
	if rule.use_json and rule.conditions:
		try:
			cond = json.loads(rule.conditions)
			if cond.get("customer_type"):
				filters.append(["customer_type", "=", cond.get("customer_type")])
		except:
			pass
			
	# Note: For Visual Builder, user should add "Customer Type" = "Individual" row explicitly
	
	customers = frappe.get_all("Customer", 
		filters=filters,
		fields=["name", "customer_name", "mobile_no"]
	)
	
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
	item_code = None
	
	# Try extracting item_code from JSON
	if rule.use_json and rule.conditions:
		try:
			conditions = json.loads(rule.conditions)
			item_code = conditions.get("item_code")
		except:
			pass
			
	# Try extracting item_code from Visual Builder
	if not item_code and rule.condition_table:
		for row in rule.condition_table:
			if row.field == "item_code" and row.operator == "Equals":
				item_code = row.value
				break
	
	if not item_code:
		return
	
	days_ago = rule.days_interval or 30
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

def process_customer_group(rule):
	"""Process customer group based triggers"""
	# Get base filters from rule
	filters = get_filters_from_rule(rule)
	
	# Add mandatory filters
	filters.append(["mobile_no", "!=", ""])
	filters.append(["sms_enabled", "!=", 0])
	
	# Handle special 'customer_group' field from JSON or Table
	if rule.use_json and rule.conditions:
		try:
			cond = json.loads(rule.conditions)
			if cond.get("customer_group"):
				filters.append(["customer_group", "=", cond.get("customer_group")])
		except:
			pass
			
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