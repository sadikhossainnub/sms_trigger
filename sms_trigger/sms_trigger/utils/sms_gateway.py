import frappe
import requests
from frappe.utils import cstr

def send_sms(mobile_no, message):
	"""Send SMS using ERPNext SMS Settings with retry logic"""
	import time
	
	# Clean mobile number
	mobile_no = cstr(mobile_no).strip()
	if not mobile_no:
		return {"success": False, "error": "Invalid mobile number"}
	
	# Retry logic for rate limiting
	max_retries = 3
	for attempt in range(max_retries):
		try:
			from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms
			frappe_send_sms([mobile_no], cstr(message), success_msg=False)
			return {"success": True, "message": "SMS sent successfully"}
			
		except Exception as e:
			error_msg = str(e)
			if "429" in error_msg or "Too Many Requests" in error_msg:
				if attempt < max_retries - 1:
					time.sleep(10)  # Wait 10 seconds before retry
					continue
			
			frappe.log_error(f"SMS sending failed: {error_msg}", "SMS Gateway Error")
			return {"success": False, "error": error_msg}
	
	return {"success": False, "error": "Max retries exceeded"}

@frappe.whitelist()
def test_sms_gateway(mobile_no, message="Test SMS from SMS Trigger"):
	"""Test SMS gateway configuration"""
	return send_sms(mobile_no, message)