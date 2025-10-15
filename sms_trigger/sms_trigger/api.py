import frappe
from frappe.utils import now_datetime, validate_email_address
import json

@frappe.whitelist()
def create_sms_trigger_rule(rule_name, trigger_type, message_template, conditions=None, frequency="Daily", days_interval=None):
	"""API to create SMS trigger rule"""
	try:
		# Validate inputs
		if not rule_name or not trigger_type or not message_template:
			frappe.throw("Rule name, trigger type, and message template are required")
		
		# Validate conditions if provided
		if conditions:
			try:
				json.loads(conditions)
			except json.JSONDecodeError:
				frappe.throw("Invalid JSON format in conditions")
		
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
		return {"success": True, "rule": doc.name, "message": f"SMS Trigger Rule '{rule_name}' created successfully"}
	except Exception as e:
		frappe.log_error(f"Error creating SMS trigger rule: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def schedule_sms(customer, message, trigger_type=None, scheduled_datetime=None):
	"""API to schedule SMS"""
	try:
		# Validate inputs
		if not customer or not message:
			frappe.throw("Customer and message are required")
		
		# Validate customer exists and has mobile number
		if not frappe.db.exists("Customer", customer):
			frappe.throw(f"Customer '{customer}' does not exist")
		
		mobile_no = frappe.get_value("Customer", customer, "mobile_no")
		if not mobile_no:
			frappe.throw(f"Customer '{customer}' does not have a mobile number")
		
		if not scheduled_datetime:
			scheduled_datetime = now_datetime()
		
		doc = frappe.get_doc({
			"doctype": "Scheduled SMS",
			"customer": customer,
			"mobile_no": mobile_no,
			"message": message,
			"trigger_type": trigger_type or "Custom",
			"scheduled_datetime": scheduled_datetime
		})
		doc.insert()
		return {"success": True, "sms_id": doc.name, "message": "SMS scheduled successfully"}
	except Exception as e:
		frappe.log_error(f"Error scheduling SMS: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def send_immediate_sms(customer, message):
	"""API to send immediate SMS"""
	try:
		result = schedule_sms(customer, message, "Custom", now_datetime())
		if not result.get("success"):
			return result
		
		sms_doc = frappe.get_doc("Scheduled SMS", result["sms_id"])
		send_result = sms_doc.send_sms()
		return send_result
	except Exception as e:
		frappe.log_error(f"Error sending immediate SMS: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_sms_stats(from_date=None, to_date=None):
	"""API to get SMS statistics"""
	try:
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
				COUNT(*) as count,
				trigger_type,
				COUNT(CASE WHEN trigger_type IS NOT NULL THEN 1 END) as trigger_count
			FROM `tabScheduled SMS`
			WHERE {where_clause}
			GROUP BY status, trigger_type
		""", values, as_dict=True)
		
		total = sum(stat.count for stat in stats)
		sent_count = sum(s.count for s in stats if s.status == "Sent")
		failed_count = sum(s.count for s in stats if s.status == "Failed")
		pending_count = sum(s.count for s in stats if s.status == "Draft")
		
		return {
			"success": True,
			"total": total,
			"sent": sent_count,
			"failed": failed_count,
			"pending": pending_count,
			"stats": stats,
			"success_rate": round((sent_count / total * 100), 2) if total > 0 else 0
		}
	except Exception as e:
		frappe.log_error(f"Error getting SMS stats: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def create_bulk_sms(campaign_name, message, filter_by="All Customers", **filters):
	"""API to create bulk SMS campaign"""
	try:
		if not campaign_name or not message:
			frappe.throw("Campaign name and message are required")
		
		doc = frappe.get_doc({
			"doctype": "Bulk SMS",
			"campaign_name": campaign_name,
			"message": message,
			"filter_by": filter_by,
			**filters
		})
		doc.insert()
		return {"success": True, "campaign_id": doc.name, "message": f"Bulk SMS campaign '{campaign_name}' created successfully"}
	except Exception as e:
		frappe.log_error(f"Error creating bulk SMS: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

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
		parsed = json.loads(conditions)
		if not isinstance(parsed, dict):
			return {"valid": False, "error": "Conditions must be a JSON object"}
		return {"valid": True, "parsed": parsed}
	except json.JSONDecodeError as e:
		return {"valid": False, "error": f"Invalid JSON: {str(e)}"}

@frappe.whitelist()
def test_sms_rule(rule_name, test_customer=None):
	"""Test SMS rule with a specific customer"""
	try:
		if not frappe.db.exists("SMS Trigger Rule", rule_name):
			return {"success": False, "error": f"SMS Trigger Rule '{rule_name}' does not exist"}
		
		rule = frappe.get_doc("SMS Trigger Rule", rule_name)
		
		if not test_customer:
			# Get first customer with mobile number
			test_customer = frappe.db.get_value("Customer", 
				{"mobile_no": ["!=", ""], "sms_enabled": ["!=", 0]}, "name")
		
		if not test_customer:
			return {"success": False, "error": "No customer with mobile number found"}
		
		customer_doc = frappe.get_doc("Customer", test_customer)
		
		context = {
			"customer_name": customer_doc.customer_name,
			"mobile_no": customer_doc.mobile_no,
			"today": frappe.utils.today(),
			"invoice_no": "TEST-001",
			"amount": 1000,
			"item_code": "TEST-ITEM"
		}
		message = frappe.render_template(rule.message_template, context)
		
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
		frappe.log_error(f"Error testing SMS rule: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_customer_sms_history(customer, limit=50):
	"""Get SMS history for a specific customer"""
	try:
		if not frappe.db.exists("Customer", customer):
			return {"success": False, "error": f"Customer '{customer}' does not exist"}
		
		sms_history = frappe.get_all("Scheduled SMS",
			filters={"customer": customer},
			fields=["name", "trigger_type", "message", "status", "scheduled_datetime", "sent_datetime", "error_message"],
			order_by="scheduled_datetime desc",
			limit=limit
		)
		
		return {"success": True, "history": sms_history}
	except Exception as e:
		frappe.log_error(f"Error getting customer SMS history: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def retry_failed_sms(sms_id):
	"""Retry sending a failed SMS"""
	try:
		if not frappe.db.exists("Scheduled SMS", sms_id):
			return {"success": False, "error": f"SMS '{sms_id}' does not exist"}
		
		sms_doc = frappe.get_doc("Scheduled SMS", sms_id)
		
		if sms_doc.status != "Failed":
			return {"success": False, "error": "Only failed SMS can be retried"}
		
		# Reset status to Draft for retry
		sms_doc.status = "Draft"
		sms_doc.error_message = None
		sms_doc.save()
		
		# Try to send immediately
		result = sms_doc.send_sms()
		return result
	except Exception as e:
		frappe.log_error(f"Error retrying SMS: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_trigger_rule_performance():
	"""Get performance stats for each trigger rule"""
	try:
		stats = frappe.db.sql("""
			SELECT 
				str.rule_name,
				str.trigger_type,
				str.is_active,
				str.execution_count,
				COUNT(ss.name) as total_sms,
				SUM(CASE WHEN ss.status = 'Sent' THEN 1 ELSE 0 END) as sent_count,
				SUM(CASE WHEN ss.status = 'Failed' THEN 1 ELSE 0 END) as failed_count,
				ROUND(SUM(CASE WHEN ss.status = 'Sent' THEN 1 ELSE 0 END) * 100.0 / COUNT(ss.name), 2) as success_rate
			FROM `tabSMS Trigger Rule` str
			LEFT JOIN `tabScheduled SMS` ss ON ss.trigger_type = str.trigger_type
			GROUP BY str.name
			ORDER BY str.rule_name
		""", as_dict=True)
		
		return {"success": True, "stats": stats}
	except Exception as e:
		frappe.log_error(f"Error getting trigger rule performance: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def pause_all_sms_rules():
	"""Pause all active SMS trigger rules"""
	try:
		frappe.db.sql("UPDATE `tabSMS Trigger Rule` SET is_active = 0 WHERE is_active = 1")
		frappe.db.commit()
		return {"success": True, "message": "All SMS trigger rules have been paused"}
	except Exception as e:
		frappe.log_error(f"Error pausing SMS rules: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def resume_all_sms_rules():
	"""Resume all paused SMS trigger rules"""
	try:
		frappe.db.sql("UPDATE `tabSMS Trigger Rule` SET is_active = 1 WHERE is_active = 0")
		frappe.db.commit()
		return {"success": True, "message": "All SMS trigger rules have been resumed"}
	except Exception as e:
		frappe.log_error(f"Error resuming SMS rules: {str(e)}", "SMS Trigger API Error")
		return {"success": False, "error": str(e)}