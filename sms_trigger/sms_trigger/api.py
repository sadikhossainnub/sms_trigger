import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def create_sms_trigger_rule(rule_name, trigger_type, message_template, conditions=None, frequency="Daily", days_interval=None):
	"""API to create SMS trigger rule"""
	doc = frappe.get_doc({
		"doctype": "SMS Trigger Rule",
		"rule_name": rule_name,
		"trigger_type": trigger_type,
		"message_template": message_template,
		"conditions": conditions,
		"frequency": frequency,
		"days_interval": days_interval,
		"is_active": 1
	})
	doc.insert()
	return doc

@frappe.whitelist()
def schedule_sms(customer, message, trigger_type=None, scheduled_datetime=None):
	"""API to schedule SMS"""
	if not scheduled_datetime:
		scheduled_datetime = now_datetime()
	
	doc = frappe.get_doc({
		"doctype": "Scheduled SMS",
		"customer": customer,
		"message": message,
		"trigger_type": trigger_type or "Custom",
		"scheduled_datetime": scheduled_datetime
	})
	doc.insert()
	return doc

@frappe.whitelist()
def send_immediate_sms(customer, message):
	"""API to send immediate SMS"""
	doc = schedule_sms(customer, message, "Custom", now_datetime())
	return doc.send_sms()

@frappe.whitelist()
def get_sms_stats(from_date=None, to_date=None):
	"""API to get SMS statistics"""
	conditions = []
	values = []
	
	if from_date:
		conditions.append("scheduled_datetime >= %s")
		values.append(from_date)
	
	if to_date:
		conditions.append("scheduled_datetime <= %s")
		values.append(to_date)
	
	where_clause = " AND ".join(conditions) if conditions else "1=1"
	
	stats = frappe.db.sql(f"""
		SELECT 
			status,
			COUNT(*) as count
		FROM `tabScheduled SMS`
		WHERE {where_clause}
		GROUP BY status
	""", values, as_dict=True)
	
	total = sum(stat.count for stat in stats)
	
	return {
		"total": total,
		"stats": stats,
		"success_rate": (next((s.count for s in stats if s.status == "Sent"), 0) / total * 100) if total > 0 else 0
	}

@frappe.whitelist()
def create_bulk_sms(campaign_name, message, filter_by="All Customers", **filters):
	"""API to create bulk SMS campaign"""
	doc = frappe.get_doc({
		"doctype": "Bulk SMS",
		"campaign_name": campaign_name,
		"message": message,
		"filter_by": filter_by,
		**filters
	})
	doc.insert()
	return doc

@frappe.whitelist()
def enable_sms_rule(rule_name):
	"""Enable SMS trigger rule"""
	rule = frappe.get_doc("SMS Trigger Rule", rule_name)
	rule.enable_rule()
	return {"success": True, "message": f"Rule '{rule_name}' enabled"}

@frappe.whitelist()
def disable_sms_rule(rule_name):
	"""Disable SMS trigger rule"""
	rule = frappe.get_doc("SMS Trigger Rule", rule_name)
	rule.disable_rule()
	return {"success": True, "message": f"Rule '{rule_name}' disabled"}

@frappe.whitelist()
def toggle_sms_rule(rule_name):
	"""Toggle SMS trigger rule status"""
	rule = frappe.get_doc("SMS Trigger Rule", rule_name)
	if rule.is_active:
		rule.disable_rule()
		status = "disabled"
	else:
		rule.enable_rule()
		status = "enabled"
	return {"success": True, "message": f"Rule '{rule_name}' {status}"}

@frappe.whitelist()
def validate_sms_conditions(conditions):
	"""Validate SMS trigger conditions JSON"""
	try:
		import json
		parsed = json.loads(conditions)
		if not isinstance(parsed, dict):
			return {"valid": False, "error": "Conditions must be a JSON object"}
		return {"valid": True, "parsed": parsed}
	except json.JSONDecodeError as e:
		return {"valid": False, "error": f"Invalid JSON: {str(e)}"}

@frappe.whitelist()
def test_sms_rule(rule_name, test_customer=None):
	"""Test SMS rule with a specific customer"""
	rule = frappe.get_doc("SMS Trigger Rule", rule_name)
	
	if not test_customer:
		# Get first customer with mobile number
		test_customer = frappe.db.get_value("Customer", 
			{"mobile_no": ["!=", ""]}, "name")
	
	if not test_customer:
		return {"success": False, "error": "No customer with mobile number found"}
	
	customer_doc = frappe.get_doc("Customer", test_customer)
	
	try:
		message = rule.message_template.format(
			customer_name=customer_doc.customer_name
		)
		
		from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
		result = send_sms(customer_doc.mobile_no, message)
		
		return {
			"success": result.get("success", False),
			"message": message,
			"customer": test_customer,
			"mobile_no": customer_doc.mobile_no,
			"result": result
		}
	except Exception as e:
		return {"success": False, "error": str(e)}