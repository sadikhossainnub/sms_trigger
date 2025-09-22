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