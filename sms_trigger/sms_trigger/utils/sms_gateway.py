import frappe
import requests
from frappe.utils import cstr, now_datetime, get_datetime
import time
import re
from frappe.core.doctype.sms_settings.sms_settings import validate_receiver_nos

# Rate limiting cache
sms_rate_limit = {}

def send_sms(mobile_no, message, max_retries=3, retry_delay=5):
	"""Send SMS using ERPNext SMS Settings with retry mechanism and rate limiting"""
	# Clean and validate mobile number
	mobile_no = clean_mobile_number(mobile_no)
	if not mobile_no:
		return {"success": False, "error": "Invalid mobile number"}
	
	# Check rate limiting
	if is_rate_limited(mobile_no):
		return {"success": False, "error": "Rate limit exceeded for this number"}
	
	# Validate message
	if not message or len(message.strip()) == 0:
		return {"success": False, "error": "Message cannot be empty"}
	
	if len(message) > 1600:  # SMS character limit
		message = message[:1600]
	
	for attempt in range(max_retries):
		try:
			from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms
			
			# Check if SMS settings are configured
			sms_settings = frappe.get_single("SMS Settings")
			if not sms_settings.sms_gateway_url:
				return {"success": False, "error": "SMS Gateway not configured in SMS Settings"}
			
			frappe_send_sms([mobile_no], cstr(message), success_msg=False)
			update_rate_limit(mobile_no)
			frappe.log_info(f"SMS sent successfully to {mobile_no}", "SMS Gateway")
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
	frappe.log_error("SMS sending failed with unknown error", "SMS Gateway Error")
	return {"success": False, "error": "Unknown error during SMS sending"}

def clean_mobile_number(mobile_no):
	"""Clean and validate mobile number"""
	if not mobile_no:
		return None
	
	# Remove all non-digit characters
	mobile_no = re.sub(r'\D', '', cstr(mobile_no).strip())
	
	# Basic validation - should be between 10-15 digits
	if len(mobile_no) < 10 or len(mobile_no) > 15:
		return None
	
	return mobile_no

def is_rate_limited(mobile_no):
	"""Check if mobile number is rate limited (max 5 SMS per hour)"""
	current_time = now_datetime()
	if mobile_no not in sms_rate_limit:
		return False
	
	# Clean old entries
	sms_rate_limit[mobile_no] = [t for t in sms_rate_limit[mobile_no] 
								if (current_time - t).total_seconds() < 3600]
	
	return len(sms_rate_limit[mobile_no]) >= 5

def update_rate_limit(mobile_no):
	"""Update rate limit tracking"""
	if mobile_no not in sms_rate_limit:
		sms_rate_limit[mobile_no] = []
	sms_rate_limit[mobile_no].append(now_datetime())

@frappe.whitelist()
def test_sms_gateway(mobile_no, message="Test SMS from SMS Trigger"):
	"""Test SMS gateway configuration"""
	result = send_sms(mobile_no, message)
	
	# Log test result
	if result.get("success"):
		frappe.msgprint(f"Test SMS sent successfully to {mobile_no}")
	else:
		frappe.msgprint(f"Test SMS failed: {result.get('error')}", indicator="red")
	
	return result

@frappe.whitelist()
def get_sms_settings_status():
	"""Check SMS settings configuration"""
	try:
		sms_settings = frappe.get_single("SMS Settings")
		if not sms_settings.sms_gateway_url:
			return {"configured": False, "error": "SMS Gateway URL not configured"}
		return {"configured": True, "gateway": sms_settings.sms_gateway_url}
	except Exception as e:
		return {"configured": False, "error": str(e)}