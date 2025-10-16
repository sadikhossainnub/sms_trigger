import frappe
from frappe.utils import now_datetime, flt

def send_pos_invoice_sms(doc, method):
	"""Send SMS to customer when POS Invoice is submitted"""
	try:
		# Get SMS settings
		sms_settings = frappe.get_single("SMS Trigger Settings")
		
		# Check if POS SMS is enabled
		if not sms_settings.enable_pos_sms:
			return
		
		# Check minimum amount
		if flt(doc.grand_total) < flt(sms_settings.pos_min_amount):
			return
		
		# Check if customer exists and has mobile number
		if not doc.customer:
			return
		
		customer = frappe.get_doc("Customer", doc.customer)
		if not customer.mobile_no or not getattr(customer, 'sms_enabled', 1):
			return
		
		# Check customer type filter
		if sms_settings.pos_customer_types:
			allowed_types = [t.strip() for t in sms_settings.pos_customer_types.split(',') if t.strip()]
			if customer.customer_type not in allowed_types:
				return
		
		# Prepare context for template
		context = {
			"customer_name": customer.customer_name,
			"invoice_no": doc.name,
			"amount": doc.grand_total,
			"date": doc.posting_date,
			"company": doc.company,
			"items": get_item_list(doc),
			"payment_mode": get_payment_mode(doc)
		}
		
		# Render message
		message = frappe.render_template(sms_settings.pos_sms_template, context)
		
		# Create scheduled SMS
		sms_doc = frappe.get_doc({
			"doctype": "Scheduled SMS",
			"customer": doc.customer,
			"mobile_no": customer.mobile_no,
			"message": message,
			"trigger_type": "POS Invoice",
			"scheduled_datetime": now_datetime(),
			"reference_doctype": "POS Invoice",
			"reference_name": doc.name
		})
		sms_doc.insert(ignore_permissions=True)
		
		# Send immediately
		sms_doc.send_sms()
		
	except Exception as e:
		frappe.log_error(f"Error sending POS Invoice SMS for {doc.name}: {str(e)}", "POS SMS Error")

def get_item_list(doc):
	"""Get formatted item list"""
	try:
		items = []
		for item in doc.items[:3]:  # Show max 3 items
			items.append(f"{item.item_name} ({item.qty})")
		if len(doc.items) > 3:
			items.append(f"and {len(doc.items) - 3} more items")
		return ", ".join(items)
	except Exception:
		return "Items purchased"

def get_payment_mode(doc):
	"""Get payment mode"""
	try:
		if doc.payments:
			return doc.payments[0].mode_of_payment
		return "Cash"
	except Exception:
		return "Cash"

@frappe.whitelist()
def get_pos_sms_preview(template, customer=None):
	"""Preview POS SMS template"""
	try:
		if not customer:
			customer = frappe.db.get_value("Customer", {"mobile_no": ["!=", ""]}, "name")
		
		if customer:
			customer_doc = frappe.get_doc("Customer", customer)
			context = {
				"customer_name": customer_doc.customer_name,
				"invoice_no": "POS-INV-001",
				"amount": "1,500.00",
				"date": frappe.utils.today(),
				"company": frappe.defaults.get_user_default("Company"),
				"items": "Item 1 (2), Item 2 (1)",
				"payment_mode": "Cash"
			}
		else:
			context = {
				"customer_name": "John Doe",
				"invoice_no": "POS-INV-001",
				"amount": "1,500.00",
				"date": frappe.utils.today(),
				"company": "Your Company",
				"items": "Item 1 (2), Item 2 (1)",
				"payment_mode": "Cash"
			}
		
		return frappe.render_template(template, context)
	except Exception as e:
		return f"Error: {str(e)}"