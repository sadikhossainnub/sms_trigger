import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime
import json

class BulkSMS(Document):
	def validate(self):
		if not self.send_immediately and not self.scheduled_datetime:
			frappe.throw("Please set scheduled date time or check send immediately")
		
		if self.custom_filter:
			try:
				json.loads(self.custom_filter)
			except:
				frappe.throw("Invalid JSON format in custom filter")
	
	def before_save(self):
		self.load_recipients()
	
	def load_recipients(self):
		"""Load recipients based on filter criteria"""
		customers = self.get_filtered_customers()
		
		self.recipients = []
		for customer in customers:
			if customer.mobile_no:
				self.append("recipients", {
					"customer": customer.name,
					"customer_name": customer.customer_name,
					"mobile_no": customer.mobile_no,
					"status": "Pending"
				})
		
		self.total_recipients = len(self.recipients)
	
	def get_filtered_customers(self):
		"""Get customers based on filter criteria"""
		filters = {"mobile_no": ["!=", ""]}
		
		if self.filter_by == "Customer Type" and self.customer_type:
			filters["customer_type"] = self.customer_type
		elif self.filter_by == "Customer Group" and self.customer_group:
			filters["customer_group"] = self.customer_group
		elif self.filter_by == "Territory" and self.territory:
			filters["territory"] = self.territory
		elif self.filter_by == "Gender" and self.gender:
			filters["gender"] = self.gender
		elif self.filter_by == "Religion" and self.religion:
			filters["religion"] = self.religion
		elif self.filter_by == "Custom Filter" and self.custom_filter:
			custom_filters = json.loads(self.custom_filter)
			filters.update(custom_filters)
		
		return frappe.get_all("Customer", 
			filters=filters,
			fields=["name", "customer_name", "mobile_no"]
		)
	
	@frappe.whitelist()
	def send_bulk_sms(self):
		"""Send bulk SMS to all recipients"""
		if self.status != "Draft":
			frappe.throw("Can only send SMS from Draft status")
		
		self.status = "Queued"
		self.save()
		
		# Queue background job for sending
		frappe.enqueue(
			"sms_trigger.sms_trigger.doctype.bulk_sms.bulk_sms.process_bulk_sms",
			bulk_sms_name=self.name,
			queue="default",
			timeout=3600
		)
		
		frappe.msgprint("Bulk SMS queued for sending")

def process_bulk_sms(bulk_sms_name):
	"""Background job to process bulk SMS"""
	doc = frappe.get_doc("Bulk SMS", bulk_sms_name)
	doc.status = "Sending"
	doc.save()
	
	from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
	
	success_count = 0
	failed_count = 0
	
	for recipient in doc.recipients:
		try:
			result = send_sms(recipient.mobile_no, doc.message)
			
			if result.get("success"):
				recipient.status = "Sent"
				recipient.sent_datetime = now_datetime()
				success_count += 1
			else:
				recipient.status = "Failed"
				recipient.error_message = result.get("error", "Unknown error")
				failed_count += 1
				
		except Exception as e:
			recipient.status = "Failed"
			recipient.error_message = str(e)
			failed_count += 1
	
	doc.status = "Completed" if failed_count == 0 else "Failed"
	doc.save()
	
	frappe.publish_realtime(
		"bulk_sms_completed",
		{"success": success_count, "failed": failed_count},
		user=doc.owner
	)