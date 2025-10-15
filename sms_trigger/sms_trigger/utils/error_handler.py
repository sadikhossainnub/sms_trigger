import frappe
from frappe.utils import now_datetime, cstr
import traceback

class SMSErrorHandler:
	"""Centralized error handling for SMS Trigger app"""
	
	@staticmethod
	def log_error(error, context="SMS Trigger", reference_doc=None, reference_name=None):
		"""Log error with context information"""
		try:
			error_message = cstr(error)
			stack_trace = traceback.format_exc()
			
			# Create error log entry
			error_log = frappe.get_doc({
				"doctype": "Error Log",
				"method": context,
				"error": f"{error_message}\n\nStack Trace:\n{stack_trace}",
				"reference_doctype": reference_doc,
				"reference_name": reference_name
			})
			error_log.insert(ignore_permissions=True)
			
			# Also log to frappe's error log
			frappe.log_error(error_message, context)
			
			return error_log.name
		except Exception as e:
			# Fallback logging
			frappe.log_error(f"Error in error handler: {str(e)}", "SMS Error Handler")
	
	@staticmethod
	def handle_sms_send_error(sms_doc, error):
		"""Handle SMS sending errors"""
		try:
			sms_doc.status = "Failed"
			sms_doc.error_message = cstr(error)[:500]  # Limit error message length
			sms_doc.save(ignore_permissions=True)
			
			SMSErrorHandler.log_error(
				error, 
				"SMS Send Error", 
				"Scheduled SMS", 
				sms_doc.name
			)
		except Exception as e:
			frappe.log_error(f"Error handling SMS send error: {str(e)}", "SMS Error Handler")
	
	@staticmethod
	def handle_trigger_error(rule_name, error):
		"""Handle trigger processing errors"""
		try:
			SMSErrorHandler.log_error(
				error, 
				f"SMS Trigger Rule Error - {rule_name}", 
				"SMS Trigger Rule", 
				rule_name
			)
			
			# Optionally disable rule after multiple failures
			rule = frappe.get_doc("SMS Trigger Rule", rule_name)
			rule.error_count = (rule.error_count or 0) + 1
			
			# Disable rule after 5 consecutive errors
			if rule.error_count >= 5:
				rule.is_active = 0
				frappe.msgprint(f"SMS Trigger Rule '{rule_name}' has been disabled due to repeated errors", 
					indicator="red")
			
			rule.save(ignore_permissions=True)
		except Exception as e:
			frappe.log_error(f"Error handling trigger error: {str(e)}", "SMS Error Handler")

def validate_sms_settings():
	"""Validate SMS settings configuration"""
	try:
		sms_settings = frappe.get_single("SMS Settings")
		
		if not sms_settings.sms_gateway_url:
			return {"valid": False, "error": "SMS Gateway URL not configured"}
		
		if not sms_settings.get_password("password"):
			return {"valid": False, "error": "SMS Gateway password not configured"}
		
		return {"valid": True}
	except Exception as e:
		return {"valid": False, "error": str(e)}

def get_error_summary():
	"""Get summary of recent SMS errors"""
	try:
		# Get errors from last 7 days
		from frappe.utils import add_days, getdate
		cutoff_date = add_days(getdate(), -7)
		
		errors = frappe.db.sql("""
			SELECT 
				method,
				COUNT(*) as error_count,
				MAX(creation) as last_error
			FROM `tabError Log`
			WHERE method LIKE '%SMS%'
			AND DATE(creation) >= %s
			GROUP BY method
			ORDER BY error_count DESC
		""", (cutoff_date,), as_dict=True)
		
		return {"success": True, "errors": errors}
	except Exception as e:
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_sms_health_check():
	"""Comprehensive health check for SMS system"""
	try:
		health_status = {
			"overall_status": "Healthy",
			"checks": []
		}
		
		# Check SMS Settings
		sms_validation = validate_sms_settings()
		health_status["checks"].append({
			"check": "SMS Settings",
			"status": "Pass" if sms_validation["valid"] else "Fail",
			"message": sms_validation.get("error", "SMS settings configured properly")
		})
		
		# Check active rules
		active_rules = frappe.db.count("SMS Trigger Rule", {"is_active": 1})
		health_status["checks"].append({
			"check": "Active Rules",
			"status": "Pass" if active_rules > 0 else "Warning",
			"message": f"{active_rules} active SMS trigger rules"
		})
		
		# Check pending SMS
		pending_sms = frappe.db.count("Scheduled SMS", {"status": "Draft"})
		health_status["checks"].append({
			"check": "Pending SMS",
			"status": "Warning" if pending_sms > 100 else "Pass",
			"message": f"{pending_sms} pending SMS messages"
		})
		
		# Check recent failures
		recent_failures = frappe.db.count("Scheduled SMS", {
			"status": "Failed",
			"creation": [">=", add_days(now_datetime(), -1)]
		})
		health_status["checks"].append({
			"check": "Recent Failures",
			"status": "Warning" if recent_failures > 10 else "Pass",
			"message": f"{recent_failures} failed SMS in last 24 hours"
		})
		
		# Determine overall status
		if any(check["status"] == "Fail" for check in health_status["checks"]):
			health_status["overall_status"] = "Critical"
		elif any(check["status"] == "Warning" for check in health_status["checks"]):
			health_status["overall_status"] = "Warning"
		
		return {"success": True, "health": health_status}
	except Exception as e:
		return {"success": False, "error": str(e)}