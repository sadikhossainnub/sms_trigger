import frappe
import requests
from frappe.utils import cstr

def send_sms(mobile_no, message):
	"""Send SMS using ERPNext SMS Settings (same as SMS Center)"""
	try:
		# Clean mobile number
		mobile_no = cstr(mobile_no).strip()
		if not mobile_no:
			return {"success": False, "error": "Invalid mobile number"}
		
		# Use ERPNext's SMS Center approach
		from frappe.core.doctype.sms_settings.sms_settings import send_sms as frappe_send_sms
		frappe_send_sms([mobile_no], cstr(message), success_msg=False)
		
		return {"success": True, "message": "SMS sent successfully"}
		
	except Exception as e:
		frappe.log_error(f"SMS sending failed: {str(e)}", "SMS Gateway Error")
		return {"success": False, "error": str(e)}

@frappe.whitelist()
def test_sms_gateway(mobile_no, message="Test SMS from SMS Trigger"):
	"""Test SMS gateway configuration"""
	return send_sms(mobile_no, message)