import frappe
import requests
from frappe.utils import cstr

def send_sms(mobile_no, message):
	"""Send SMS using ERPNext SMS Settings"""
	try:
		sms_settings = frappe.get_single("SMS Settings")
		
		if not sms_settings.sms_gateway_url:
			return {"success": False, "error": "SMS Gateway not configured"}
		
		# Clean mobile number
		mobile_no = cstr(mobile_no).strip()
		if not mobile_no:
			return {"success": False, "error": "Invalid mobile number"}
		
		# Prepare SMS data
		data = {
			"receiver_list": [mobile_no],
			"message": message
		}
		
		# Use ERPNext's built-in SMS sending
		from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms
		frappe_send_sms(data["receiver_list"], data["message"])
		
		return {"success": True, "message": "SMS sent successfully"}
		
	except Exception as e:
		frappe.log_error(f"SMS sending failed: {str(e)}", "SMS Gateway Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def test_sms_gateway(mobile_no, message="Test SMS from SMS Trigger"):
	"""Test SMS gateway configuration"""
	return send_sms(mobile_no, message)