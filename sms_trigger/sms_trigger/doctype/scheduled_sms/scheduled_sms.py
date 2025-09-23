import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class ScheduledSMS(Document):
	def validate(self):
		if not self.mobile_no and self.customer:
			customer = frappe.get_doc("Customer", self.customer)
			self.mobile_no = customer.mobile_no
	
	def send_sms(self):
		# Prevent duplicate sends - only send if status is Draft
		if self.status != "Draft":
			return {"success": False, "error": "SMS already processed"}
		
		try:
			from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
			result = send_sms(self.mobile_no, self.message)
			
			if result.get("success"):
				self.status = "Sent"
				self.sent_datetime = now_datetime()
			else:
				self.status = "Failed"
				self.error_message = result.get("error", "Unknown error")
			
			self.save()
			return result
			
		except Exception as e:
			self.status = "Failed"
			self.error_message = str(e)
			self.save()
			return {"success": False, "error": str(e)}