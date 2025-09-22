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
	
	@frappe.whitelist()
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
		
		if self.filter_by == "Customer Group" and self.customer_group:
			filters["customer_group"] = self.customer_group
		elif self.filter_by == "Territory" and self.territory:
			filters["territory"] = self.territory
		elif self.filter_by == "Gender" and self.gender:
			filters["gender"] = self.gender
		elif self.filter_by == "Religion" and self.religion:
			filters["religion"] = self.religion
		elif self.filter_by == "Profession" and self.profession:
			filters["profession"] = self.profession
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
		
		# Create queue log
		create_sms_queue_log(self)
		
		# Queue background job for sending
		frappe.enqueue(
			"sms_trigger.sms_trigger.doctype.bulk_sms.bulk_sms.process_bulk_sms",
			bulk_sms_name=self.name,
			queue="default",
			timeout=3600
		)
		
		frappe.msgprint("Bulk SMS queued for sending")
	
	@frappe.whitelist()
	def retry_failed_sms(self):
		"""Retry sending failed SMS"""
		if self.status not in ["Failed", "Completed"]:
			frappe.throw("Can only retry from Failed or Completed status")
		
		# Reset failed recipients to pending
		failed_count = 0
		for recipient in self.recipients:
			if recipient.status == "Failed":
				recipient.status = "Pending"
				recipient.error_message = ""
				failed_count += 1
		
		if failed_count == 0:
			frappe.throw("No failed SMS to retry")
		
		self.status = "Queued"
		self.save()
		
		# Queue background job for retry
		frappe.enqueue(
			"sms_trigger.sms_trigger.doctype.bulk_sms.bulk_sms.process_bulk_sms",
			bulk_sms_name=self.name,
			queue="default",
			timeout=3600
		)
		
		frappe.msgprint(f"Retrying {failed_count} failed SMS")

def process_bulk_sms(bulk_sms_name):
	"""Background job to process bulk SMS"""
	doc = frappe.get_doc("Bulk SMS", bulk_sms_name)
	doc.reload()
	doc.status = "Sending"
	doc.save(ignore_version=True)
	
	# Update queue log
	update_sms_queue_log(bulk_sms_name, "Processing", started_datetime=now_datetime())
	
	from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
	
	success_count = 0
	failed_count = 0
	
	for recipient in doc.recipients:
		# Only process pending SMS (for retry functionality)
		if recipient.status != "Pending":
			if recipient.status == "Sent":
				success_count += 1
			elif recipient.status == "Failed":
				failed_count += 1
			continue
			
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
			
			# Create log entry
			create_bulk_sms_log(doc, recipient)
			
			# Add delay to avoid rate limiting
			import time
			time.sleep(3)  # 3 second delay between SMS
				
		except Exception as e:
			recipient.status = "Failed"
			recipient.error_message = str(e)
			failed_count += 1
			
			# Create log entry
			create_bulk_sms_log(doc, recipient)
	
	# Save recipient status updates
	doc.save(ignore_version=True)
	
	doc.status = "Completed" if failed_count == 0 else "Failed"
	doc.save(ignore_version=True)
	
	# Update final queue log
	update_sms_queue_log(
		bulk_sms_name, 
		"Completed" if failed_count == 0 else "Failed",
		completed_datetime=now_datetime(),
		success_count=success_count,
		failed_count=failed_count
	)
	
	frappe.publish_realtime(
		"bulk_sms_completed",
		{"success": success_count, "failed": failed_count},
		user=doc.owner
	)

def create_bulk_sms_log(bulk_sms_doc, recipient):
	"""Create log entry for each SMS sent"""
	frappe.get_doc({
		"doctype": "Bulk SMS Log",
		"bulk_sms": bulk_sms_doc.name,
		"customer": recipient.customer,
		"customer_name": recipient.customer_name,
		"mobile_no": recipient.mobile_no,
		"message": bulk_sms_doc.message,
		"status": recipient.status,
		"sent_datetime": recipient.sent_datetime,
		"error_message": recipient.error_message
	}).insert()

def create_sms_queue_log(bulk_sms_doc):
	"""Create SMS queue log entry"""
	frappe.get_doc({
		"doctype": "SMS Queue Log",
		"bulk_sms": bulk_sms_doc.name,
		"queue_status": "Queued",
		"queued_datetime": now_datetime(),
		"total_recipients": bulk_sms_doc.total_recipients
	}).insert()

def update_sms_queue_log(bulk_sms_name, status, **kwargs):
	"""Update SMS queue log"""
	queue_log = frappe.db.get_value("SMS Queue Log", {"bulk_sms": bulk_sms_name}, "name")
	if queue_log:
		doc = frappe.get_doc("SMS Queue Log", queue_log)
		doc.queue_status = status
		
		for key, value in kwargs.items():
			setattr(doc, key, value)
		
		if kwargs.get("success_count") and kwargs.get("failed_count"):
			total = kwargs["success_count"] + kwargs["failed_count"]
			doc.success_rate = (kwargs["success_count"] / total * 100) if total > 0 else 0
		
		doc.save()