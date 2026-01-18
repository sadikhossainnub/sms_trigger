import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime
import json

class BulkSMS(Document):
	def validate(self):
		pass  # Remove send_immediately validation
		
		if self.custom_filter:
			try:
				json.loads(self.custom_filter)
			except json.JSONDecodeError:
				frappe.throw("Invalid JSON format in custom filter")
		
		if not self.message:
			frappe.throw("Message is required")
		
		if len(self.message) > 1600:
			frappe.throw("Message cannot exceed 1600 characters")

		# Validate recipients on save
		if self.recipients:
			for r in self.recipients:
				if r.status not in ["Sent"]: # Don't touch sent ones
					if not r.mobile_no or len(r.mobile_no) < 5:
						r.status = "Invalid"
						r.error_message = "Invalid Mobile Number length"
					elif r.status == "Invalid": # Auto-recover if fixed
						r.status = "Pending"
						r.error_message = None

	def before_save(self):
		# Only auto-load if no manual recipients exist
		if not self.recipients and self.filter_by:
			self.load_recipients()
		# Update total count
		self.total_recipients = len(self.recipients)
	
	@frappe.whitelist()
	def load_recipients(self):
		"""Load recipients based on filter criteria"""
		customers = self.get_filtered_customers()
		
		# Clear existing recipients only when explicitly loading
		self.recipients = []
		for customer in customers:
			status = "Pending"
			error = None
			if not customer.mobile_no or len(customer.mobile_no) < 5:
				status = "Invalid"
				error = "Invalid Mobile Number length"

			if customer.mobile_no: # Still only add existing ones? Or all? 
                # Original logic: only if customer.mobile_no:
                # But "Invalid" implies we added it but it's bad.
                # If mobile_no is Empty, usually we skip it. 
                # "Load Recipients" should probably SKIP empty numbers. 
                # "Invalid" is for "000" or "abc".
                # Let's keep existing logic: check if customer.mobile_no exists.
				self.append("recipients", {
					"customer": customer.name,
					"customer_name": customer.customer_name,
					"mobile_no": customer.mobile_no,
					"status": status,
                    "error_message": error
				})
		
		self.total_recipients = len(self.recipients)
		
		if self.total_recipients == 0:
			frappe.msgprint("No recipients found matching criteria. Ensure customers have Mobile No and SMS Enabled.")
			
		return self.recipients
	

	
	def get_filtered_customers(self):
		"""Get customers based on filter criteria"""
		if not self.filter_by:
			return []  # Manual selection - no auto-load
		
		if self.filter_by == "All Customers":
			pass  # Use base filters only
		
		filters = {"mobile_no": ["!=", ""], "sms_enabled": ["!=", 0]}
		
		from frappe.utils.nestedset import get_descendants_of
		
		if self.filter_by == "Customer Group" and self.customer_group:
			groups = get_descendants_of("Customer Group", self.customer_group)
			groups.append(self.customer_group)
			filters["customer_group"] = ["in", groups]
			
		elif self.filter_by == "Territory" and self.territory:
			territories = get_descendants_of("Territory", self.territory)
			territories.append(self.territory)
			filters["territory"] = ["in", territories]
			
		elif self.filter_by == "Gender" and self.gender:
			filters["gender"] = self.gender
		elif self.filter_by == "Religion" and self.religion:
			filters["religion"] = self.religion
		elif self.filter_by == "Profession" and self.profession:
			filters["profession"] = self.profession
		elif self.filter_by == "Custom Filter" and self.custom_filter:
			try:
				custom_filters = json.loads(self.custom_filter)
				filters.update(custom_filters)
			except json.JSONDecodeError:
				frappe.throw("Invalid JSON format in custom filter")
		
		return frappe.get_all("Customer", 
			filters=filters,
			fields=["name", "customer_name", "mobile_no"]
		)
	
	def on_submit(self):
		"""Auto-send SMS when document is submitted"""
		self.send_bulk_sms()
	
	@frappe.whitelist()
	def send_bulk_sms(self):
		"""Send bulk SMS to all recipients"""
		if self.docstatus != 1:
			frappe.throw("Document must be submitted to send SMS")
		
		# Check for scheduling
		if self.scheduled_datetime and get_datetime(self.scheduled_datetime) > now_datetime():
			self.status = "Scheduled"
			self.save()
			frappe.msgprint(f"Bulk SMS scheduled for {self.scheduled_datetime}")
		else:
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
		if self.docstatus != 1 or self.status not in ["Failed", "Completed"]:
			frappe.throw("Can only retry from Failed or Completed status on submitted document")
		
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
	
	def update_counts(self):
		"""Update success and failed counts"""
		success_count = 0
		failed_count = 0
		
		for recipient in self.recipients:
			if recipient.status == "Sent":
				success_count += 1
			elif recipient.status == "Failed":
				failed_count += 1
		
		self.success_count = success_count
		self.failed_count = failed_count
		self.save(ignore_version=True, ignore_permissions=True)

def process_bulk_sms(bulk_sms_name):
	"""Background job to process bulk SMS"""
	doc = frappe.get_doc("Bulk SMS", bulk_sms_name)
	# doc.reload() # No need to reload if we use set_value for status first
	frappe.db.set_value("Bulk SMS", bulk_sms_name, "status", "Sending")
	frappe.db.commit() # Ensure status is committed
	doc.reload() # Reload to get correct modified timestamp
	
	# Update queue log
	update_sms_queue_log(bulk_sms_name, "Processing", started_datetime=now_datetime())
	
	from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
	
	success_count = 0
	failed_count = 0
	
	processed_count = 0
	for recipient in doc.recipients:
		# Only process pending SMS (for retry functionality)
		if recipient.status != "Pending":
			if recipient.status == "Sent":
				success_count += 1
			elif recipient.status == "Failed" or recipient.status == "Invalid":
				failed_count += 1
			continue
			
		try:
			# Validate Mobile Number
			if not recipient.mobile_no or len(recipient.mobile_no) < 5: 
				# Basic length check, can be improved with regex or phonenumbers lib
				recipient.status = "Invalid"
				recipient.error_message = "Invalid Mobile Number length"
				failed_count += 1
				processed_count += 1
				create_bulk_sms_log(doc, recipient)
				continue

			context = {
				"customer": recipient.customer,
				"customer_name": recipient.customer_name,
				"mobile_no": recipient.mobile_no,
				"campaign_name": doc.campaign_name
			}
			message = frappe.render_template(doc.message, context)
			result = send_sms(recipient.mobile_no, message)
			
			if result.get("success"):
				recipient.status = "Sent"
				recipient.sent_datetime = now_datetime()
				success_count += 1
			else:
				recipient.status = "Failed"
				recipient.error_message = result.get("error", "Unknown error")
				failed_count += 1
			
			# Create log entry
			create_bulk_sms_log(doc, recipient, message=message)
			
			processed_count += 1
			
			# Save progress and publish update every 1 SMS (Immediate feedback)
			doc.update_counts()
			frappe.publish_realtime(
				"bulk_sms_progress",
				{"processed": processed_count, "success": success_count, "failed": failed_count},
				user=doc.owner
			)
			
			# Add delay to avoid rate limiting
			import time
			time.sleep(3)  # 3 second delay between SMS
				
		except Exception as e:
			recipient.status = "Failed"
			recipient.error_message = str(e)
			failed_count += 1
			processed_count += 1
			
			# Create log entry
			create_bulk_sms_log(doc, recipient)
			
			# Save progress and publish update every 1 SMS (Immediate feedback)
			doc.update_counts()
			frappe.publish_realtime(
				"bulk_sms_progress",
				{"processed": processed_count, "success": success_count, "failed": failed_count},
				user=doc.owner
			)


	# Update counts and save
	doc.update_counts()
	doc.status = "Completed" if failed_count == 0 else "Failed"
	doc.save(ignore_version=True, ignore_permissions=True)
	
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

def create_bulk_sms_log(bulk_sms_doc, recipient, message=None):
	"""Create log entry for each SMS sent"""
	frappe.get_doc({
		"doctype": "Bulk SMS Log",
		"bulk_sms": bulk_sms_doc.name,
		"customer": recipient.customer,
		"customer_name": recipient.customer_name,
		"mobile_no": recipient.mobile_no,
		"message": message or bulk_sms_doc.message,
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

def process_scheduled_campaigns():
	"""Process scheduled bulk sms campaigns"""
	scheduled_campaigns = frappe.get_all("Bulk SMS",
		filters={
			"status": "Scheduled",
			"docstatus": 1,
			"scheduled_datetime": ["<=", now_datetime()]
		},
		fields=["name"]
	)
	
	for campaign in scheduled_campaigns:
		# Double check status to avoid race conditions
		doc = frappe.get_doc("Bulk SMS", campaign.name)
		if doc.status == "Scheduled":
			doc.status = "Queued"
			doc.save()
			
			create_sms_queue_log(doc)
			
			frappe.enqueue(
				"sms_trigger.sms_trigger.doctype.bulk_sms.bulk_sms.process_bulk_sms",
				bulk_sms_name=doc.name,
				queue="default",
				timeout=3600
			)