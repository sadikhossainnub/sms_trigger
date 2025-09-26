import frappe
import requests
from frappe.utils import cstr
import time

def send_sms(mobile_no, message, max_retries=3, retry_delay=5):
	"""Send SMS using ERPNext SMS Settings with retry mechanism"""
	# Clean mobile number
	mobile_no = cstr(mobile_no).strip()
	if not mobile_no:
		return {"success": False, "error": "Invalid mobile number"}
	
	for attempt in range(max_retries):
		try:
			from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms
			frappe_send_sms([mobile_no], cstr(message), success_msg=False)
			return {"success": True, "message": "SMS sent successfully"}
			
		except requests.exceptions.RequestException as e:
			error_msg = f"Attempt {attempt + 1} failed: Network or API error: {str(e)}"
			if attempt < max_retries - 1:
				frappe.log_warning(error_msg, "SMS Gateway Retry")
				time.sleep(retry_delay * (2 ** attempt)) # Exponential backoff
			else:
				frappe.log_error(f"SMS sending failed after {max_retries} attempts: {error_msg}", "SMS Gateway Error")
				return {"success": False, "error": error_msg}
		except Exception as e:
			error_msg = str(e)
			frappe.log_error(f"SMS sending failed: {error_msg}", "SMS Gateway Error")
			return {"success": False, "error": error_msg}
	return {"success": False, "error": "Unknown error during SMS sending"}

@frappe.whitelist()
def test_sms_gateway(mobile_no, message="Test SMS from SMS Trigger"):
	"""Test SMS gateway configuration"""
	return send_sms(mobile_no, message)