import frappe
from frappe.utils import now_datetime, getdate, add_days
import json

@frappe.whitelist()
def validate_app_installation():
	"""Comprehensive validation of SMS Trigger app installation"""
	validation_results = {
		"overall_status": "Pass",
		"checks": [],
		"warnings": [],
		"errors": []
	}
	
	try:
		# Check DocTypes
		doctypes_check = validate_doctypes()
		validation_results["checks"].append(doctypes_check)
		
		# Check Custom Fields
		fields_check = validate_custom_fields()
		validation_results["checks"].append(fields_check)
		
		# Check Scheduler Jobs
		scheduler_check = validate_scheduler_jobs()
		validation_results["checks"].append(scheduler_check)
		
		# Check SMS Settings
		sms_check = validate_sms_configuration()
		validation_results["checks"].append(sms_check)
		
		# Check Default Rules
		rules_check = validate_default_rules()
		validation_results["checks"].append(rules_check)
		
		# Check API Endpoints
		api_check = validate_api_endpoints()
		validation_results["checks"].append(api_check)
		
		# Determine overall status
		if any(check["status"] == "Fail" for check in validation_results["checks"]):
			validation_results["overall_status"] = "Fail"
		elif any(check["status"] == "Warning" for check in validation_results["checks"]):
			validation_results["overall_status"] = "Warning"
		
		return validation_results
		
	except Exception as e:
		validation_results["overall_status"] = "Error"
		validation_results["errors"].append(f"Validation error: {str(e)}")
		return validation_results

def validate_doctypes():
	"""Validate required doctypes exist"""
	required_doctypes = [
		"SMS Trigger Rule",
		"Scheduled SMS", 
		"Bulk SMS",
		"Bulk SMS Log",
		"Bulk SMS Recipient",
		"SMS Queue Log"
	]
	
	missing_doctypes = []
	for doctype in required_doctypes:
		if not frappe.db.exists("DocType", doctype):
			missing_doctypes.append(doctype)
	
	if missing_doctypes:
		return {
			"check": "DocTypes",
			"status": "Fail",
			"message": f"Missing doctypes: {', '.join(missing_doctypes)}"
		}
	else:
		return {
			"check": "DocTypes", 
			"status": "Pass",
			"message": f"All {len(required_doctypes)} required doctypes exist"
		}

def validate_custom_fields():
	"""Validate custom fields are created"""
	required_fields = [
		{"dt": "Customer", "fieldname": "sms_enabled"},
		{"dt": "Customer", "fieldname": "date_of_birth"}
	]
	
	missing_fields = []
	for field in required_fields:
		if not frappe.db.exists("Custom Field", field):
			missing_fields.append(f"{field['dt']}.{field['fieldname']}")
	
	if missing_fields:
		return {
			"check": "Custom Fields",
			"status": "Warning", 
			"message": f"Missing fields: {', '.join(missing_fields)}"
		}
	else:
		return {
			"check": "Custom Fields",
			"status": "Pass",
			"message": "All custom fields created successfully"
		}

def validate_scheduler_jobs():
	"""Validate scheduler jobs are configured"""
	try:
		from sms_trigger.sms_trigger.utils.trigger_engine import process_sms_triggers, send_pending_sms
		
		# Try to import functions
		return {
			"check": "Scheduler Jobs",
			"status": "Pass", 
			"message": "Scheduler functions are accessible"
		}
	except ImportError as e:
		return {
			"check": "Scheduler Jobs",
			"status": "Fail",
			"message": f"Scheduler functions not accessible: {str(e)}"
		}

def validate_sms_configuration():
	"""Validate SMS settings"""
	try:
		sms_settings = frappe.get_single("SMS Settings")
		
		if not sms_settings.sms_gateway_url:
			return {
				"check": "SMS Configuration",
				"status": "Warning",
				"message": "SMS Gateway URL not configured"
			}
		
		return {
			"check": "SMS Configuration", 
			"status": "Pass",
			"message": "SMS Settings configured"
		}
	except Exception as e:
		return {
			"check": "SMS Configuration",
			"status": "Fail", 
			"message": f"SMS Settings error: {str(e)}"
		}

def validate_default_rules():
	"""Validate default SMS rules exist"""
	default_rules = [
		"Invoice Due Reminder",
		"Birthday Wishes", 
		"Inactive Customer Follow-up"
	]
	
	existing_rules = []
	for rule_name in default_rules:
		if frappe.db.exists("SMS Trigger Rule", {"rule_name": rule_name}):
			existing_rules.append(rule_name)
	
	return {
		"check": "Default Rules",
		"status": "Pass" if len(existing_rules) > 0 else "Warning",
		"message": f"{len(existing_rules)}/{len(default_rules)} default rules exist"
	}

def validate_api_endpoints():
	"""Validate API endpoints are accessible"""
	try:
		# Test basic API imports
		from sms_trigger.sms_trigger.api import get_sms_stats, validate_sms_conditions
		
		return {
			"check": "API Endpoints",
			"status": "Pass",
			"message": "API endpoints are accessible"
		}
	except ImportError as e:
		return {
			"check": "API Endpoints", 
			"status": "Fail",
			"message": f"API endpoints not accessible: {str(e)}"
		}

@frappe.whitelist()
def run_system_test():
	"""Run comprehensive system test"""
	test_results = {
		"overall_status": "Pass",
		"tests": []
	}
	
	try:
		# Test 1: Create test SMS rule
		test_rule_result = test_create_sms_rule()
		test_results["tests"].append(test_rule_result)
		
		# Test 2: Test SMS scheduling
		test_schedule_result = test_sms_scheduling()
		test_results["tests"].append(test_schedule_result)
		
		# Test 3: Test trigger processing
		test_trigger_result = test_trigger_processing()
		test_results["tests"].append(test_trigger_result)
		
		# Test 4: Test error handling
		test_error_result = test_error_handling()
		test_results["tests"].append(test_error_result)
		
		# Cleanup test data
		cleanup_test_data()
		
		# Determine overall status
		if any(test["status"] == "Fail" for test in test_results["tests"]):
			test_results["overall_status"] = "Fail"
		elif any(test["status"] == "Warning" for test in test_results["tests"]):
			test_results["overall_status"] = "Warning"
		
		return test_results
		
	except Exception as e:
		test_results["overall_status"] = "Error"
		test_results["error"] = str(e)
		return test_results

def test_create_sms_rule():
	"""Test SMS rule creation"""
	try:
		test_rule = frappe.get_doc({
			"doctype": "SMS Trigger Rule",
			"rule_name": "Test Rule - System Validation",
			"trigger_type": "Custom",
			"frequency": "One Time",
			"message_template": "Test message for {{ customer_name }}",
			"is_active": 0
		})
		test_rule.insert(ignore_permissions=True)
		
		return {
			"test": "SMS Rule Creation",
			"status": "Pass",
			"message": "SMS rule created successfully"
		}
	except Exception as e:
		return {
			"test": "SMS Rule Creation", 
			"status": "Fail",
			"message": f"Failed to create SMS rule: {str(e)}"
		}

def test_sms_scheduling():
	"""Test SMS scheduling functionality"""
	try:
		# Find a test customer
		test_customer = frappe.db.get_value("Customer", {"mobile_no": ["!=", ""]}, "name")
		
		if not test_customer:
			return {
				"test": "SMS Scheduling",
				"status": "Warning", 
				"message": "No customer with mobile number found for testing"
			}
		
		# Create test scheduled SMS
		test_sms = frappe.get_doc({
			"doctype": "Scheduled SMS",
			"customer": test_customer,
			"message": "Test SMS - System Validation",
			"trigger_type": "Custom",
			"scheduled_datetime": now_datetime(),
			"status": "Draft"
		})
		test_sms.insert(ignore_permissions=True)
		
		return {
			"test": "SMS Scheduling",
			"status": "Pass",
			"message": "SMS scheduled successfully"
		}
	except Exception as e:
		return {
			"test": "SMS Scheduling",
			"status": "Fail", 
			"message": f"Failed to schedule SMS: {str(e)}"
		}

def test_trigger_processing():
	"""Test trigger processing logic"""
	try:
		from sms_trigger.sms_trigger.utils.trigger_engine import process_sms_triggers
		
		# This should run without errors even if no rules are active
		process_sms_triggers()
		
		return {
			"test": "Trigger Processing",
			"status": "Pass",
			"message": "Trigger processing executed successfully"
		}
	except Exception as e:
		return {
			"test": "Trigger Processing",
			"status": "Fail",
			"message": f"Trigger processing failed: {str(e)}"
		}

def test_error_handling():
	"""Test error handling functionality"""
	try:
		from sms_trigger.sms_trigger.utils.error_handler import SMSErrorHandler
		
		# Test error logging
		SMSErrorHandler.log_error("Test error for system validation", "System Test")
		
		return {
			"test": "Error Handling",
			"status": "Pass", 
			"message": "Error handling working correctly"
		}
	except Exception as e:
		return {
			"test": "Error Handling",
			"status": "Fail",
			"message": f"Error handling failed: {str(e)}"
		}

def cleanup_test_data():
	"""Clean up test data created during validation"""
	try:
		# Delete test SMS rule
		if frappe.db.exists("SMS Trigger Rule", {"rule_name": "Test Rule - System Validation"}):
			frappe.delete_doc("SMS Trigger Rule", 
				frappe.db.get_value("SMS Trigger Rule", {"rule_name": "Test Rule - System Validation"}, "name"))
		
		# Delete test scheduled SMS
		test_sms_list = frappe.get_all("Scheduled SMS", 
			filters={"message": "Test SMS - System Validation"}, 
			fields=["name"])
		
		for sms in test_sms_list:
			frappe.delete_doc("Scheduled SMS", sms.name)
		
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error cleaning up test data: {str(e)}", "SMS Validation Cleanup")

@frappe.whitelist()
def get_system_info():
	"""Get comprehensive system information"""
	try:
		info = {
			"app_version": "1.0.0",
			"frappe_version": frappe.__version__,
			"installation_date": frappe.db.get_value("Module Def", "SMS Trigger", "creation"),
			"total_rules": frappe.db.count("SMS Trigger Rule"),
			"active_rules": frappe.db.count("SMS Trigger Rule", {"is_active": 1}),
			"total_sms_sent": frappe.db.count("Scheduled SMS", {"status": "Sent"}),
			"total_sms_failed": frappe.db.count("Scheduled SMS", {"status": "Failed"}),
			"total_sms_pending": frappe.db.count("Scheduled SMS", {"status": "Draft"}),
			"customers_with_mobile": frappe.db.count("Customer", {"mobile_no": ["!=", ""]}),
			"sms_enabled_customers": frappe.db.count("Customer", {"sms_enabled": 1})
		}
		
		# Calculate success rate
		total_processed = info["total_sms_sent"] + info["total_sms_failed"]
		info["success_rate"] = round((info["total_sms_sent"] / total_processed * 100), 2) if total_processed > 0 else 0
		
		return {"success": True, "info": info}
	except Exception as e:
		return {"success": False, "error": str(e)}