import frappe

def get_notification_config():
	"""Add SMS as notification channel"""
	return {
		"for_doctype": {
			"Sales Invoice": {
				"sms": "sms_trigger.sms_trigger.notifications.send_invoice_sms"
			},
			"Customer": {
				"sms": "sms_trigger.sms_trigger.notifications.send_customer_sms"
			}
		}
	}

def send_invoice_sms(doc, recipients):
	"""Send SMS for Sales Invoice notifications"""
	if doc.doctype == "Sales Invoice" and doc.outstanding_amount > 0:
		customer = frappe.get_doc("Customer", doc.customer)
		if customer.mobile_no:
			from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
			message = f"Dear {customer.customer_name}, your invoice {doc.name} for {doc.grand_total} is due on {doc.due_date}. Please make payment at your earliest convenience."
			send_sms(customer.mobile_no, message)

def send_customer_sms(doc, recipients):
	"""Send SMS for Customer notifications"""
	if doc.doctype == "Customer" and doc.mobile_no:
		from sms_trigger.sms_trigger.utils.sms_gateway import send_sms
		message = f"Welcome {doc.customer_name}! Thank you for choosing us. We look forward to serving you."
		send_sms(doc.mobile_no, message)