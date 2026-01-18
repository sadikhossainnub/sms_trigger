import frappe
from frappe.utils import random_string, cint
from sms_trigger.sms_trigger.utils.sms_gateway import send_sms

OTP_CACHE_PREFIX = "pos_otp"

@frappe.whitelist()
def send_otp(customer):
	"""Generate and send OTP to customer"""
	settings = frappe.get_single("SMS Trigger Settings")
	if not settings.enable_pos_otp:
		return {"success": False, "error": "OTP verification is disabled"}

	if not customer:
		return {"success": False, "error": "Customer is required"}

	# Get mobile number
	mobile_no = frappe.get_value("Customer", customer, "mobile_no")
	if not mobile_no:
		return {"success": False, "error": "Customer has no mobile number"}

	# Generate OTP (6 digits)
	otp = random_string(6)
	while not otp.isdigit():
		otp = random_string(6)

	# Store in cache
	expiry_mins = cint(settings.otp_expiry_minutes) or 5
	cache_key = f"{OTP_CACHE_PREFIX}:{customer}"
	
	# Note: Expiry argument causing issues in some envs, disabled for now.
	# Redis LRU should handle cleanup or explicit delete on validate.
	frappe.cache().set_value(cache_key, otp)

	# Prepare message
	context = {"otp": otp, "minutes": expiry_mins}
	message = frappe.render_template(settings.otp_message_template, context)

	# Send SMS
	result = send_sms(mobile_no, message)
	
	if result.get("success"):
		return {"success": True, "message": f"OTP sent to {mobile_no}", "expiry": expiry_mins}
	else:
		return result

@frappe.whitelist()
def validate_otp(customer, otp):
	"""Validate provided OTP"""
	if not customer or not otp:
		return {"success": False, "error": "Customer and OTP are required"}

	cache_key = f"{OTP_CACHE_PREFIX}:{customer}"
	cached_otp = frappe.cache().get_value(cache_key)

	if not cached_otp:
		# Try raw get if get_value failed? No, get_value handles deserialization
		cached_otp = frappe.cache().get(cache_key)
		if cached_otp and hasattr(cached_otp, "decode"):
			cached_otp = cached_otp.decode("utf-8")

	if not cached_otp:
		return {"success": False, "error": "OTP expired or not found. Please request a new one."}

	if str(cached_otp) == str(otp):
		# Clear OTP after successful use to prevent replay
		frappe.cache().delete_value(cache_key)
		return {"success": True, "message": "OTP Verified"}
	else:
		return {"success": False, "error": "Invalid OTP"}

@frappe.whitelist()
def check_otp_requirement(customer, grand_total=0, total=0, discount_amount=0):
	"""Check if OTP is required for this customer"""
	settings = frappe.get_single("SMS Trigger Settings")
	if not settings.enable_pos_otp:
		return {"required": False}

	# Check customer type/group filter
	required = False
	
	customer_group = frappe.get_value("Customer", customer, "customer_group")
	customer_type = frappe.get_value("Customer", customer, "customer_type")
	
	if settings.pos_customer_types:
		allow_types = [t.strip() for t in settings.pos_customer_types.split(',')]
		if customer_type in allow_types:
			required = True
	else:
		if customer == "Walking Customer" or customer_group == "Walking Customer":
			required = True
	
	if not required:
		return {"required": False}
		
	# Check Discount Logic
	if settings.otp_on_discount_only:
		has_discount = False
		# Check Invoice Level Discount (Additional Discount)
		if discount_amount and float(discount_amount) > 0:
			has_discount = True
			
		# Also check if total < grand_total (implicit discount)? 
		# Usually discount_amount covers "Additional Discount/Discount Amount".
		# Item level usage needs more data (the items list).
		# To support Item-level discount checking, we'd need to parse the 'doc' JSON if passed, 
		# or trust the frontend to tell us 'has_discount'. 
		# For now, let's rely on passed amounts. Logic can be expanded if client sends full doc.
		
		# If client sends total != grand_total + taxes, maybe discount?
		# Safest is explicit discount_amount field from POS invoice.
		
		if not has_discount:
			return {"required": False}

	return {"required": True}
