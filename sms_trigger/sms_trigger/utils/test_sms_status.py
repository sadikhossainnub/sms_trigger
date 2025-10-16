import frappe
from frappe.utils import now_datetime

@frappe.whitelist()
def test_sms_status_update():
	"""Test function to verify SMS status updates are working"""
	try:
		# Create a test SMS
		test_sms = frappe.get_doc({
			"doctype": "Scheduled SMS",
			"customer": frappe.db.get_value("Customer", {"mobile_no": ["!=", ""]}, "name"),
			"mobile_no": "1234567890",  # Test number
			"message": "Test SMS for status update",
			"trigger_type": "Test",
			"scheduled_datetime": now_datetime()
		})
		test_sms.insert(ignore_permissions=True)
		test_sms.submit()
		
		# Try to send the SMS
		result = test_sms.send_sms()
		
		# Reload to check status
		test_sms.reload()
		
		return {
			"success": True,
			"sms_name": test_sms.name,
			"status": test_sms.status,
			"error_message": test_sms.error_message,
			"send_result": result
		}
		
	except Exception as e:
		frappe.log_error(f"Test SMS status error: {str(e)}", "SMS Test Error")
		return {
			"success": False,
			"error": str(e)
		}

@frappe.whitelist()
def check_pending_sms_count():
	"""Check how many pending SMS are in the system"""
	try:
		pending_count = frappe.db.count("Scheduled SMS", {
			"status": "Draft",
			"docstatus": 1
		})
		
		sent_count = frappe.db.count("Scheduled SMS", {
			"status": "Sent"
		})
		
		failed_count = frappe.db.count("Scheduled SMS", {
			"status": "Failed"
		})
		
		return {
			"pending": pending_count,
			"sent": sent_count,
			"failed": failed_count,
			"total": pending_count + sent_count + failed_count
		}
		
	except Exception as e:
		return {"error": str(e)}

@frappe.whitelist()
def force_send_pending():
	"""Force send all pending SMS to test status updates"""
	try:
		from sms_trigger.sms_trigger.utils.trigger_engine import send_pending_sms
		send_pending_sms()
		return {"success": True, "message": "Pending SMS processing completed"}
	except Exception as e:
		return {"success": False, "error": str(e)}