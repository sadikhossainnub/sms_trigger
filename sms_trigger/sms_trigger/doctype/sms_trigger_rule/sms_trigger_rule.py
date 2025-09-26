import frappe
from frappe.model.document import Document
import json

class SMSTriggerRule(Document):
	def validate(self):
		self.validate_conditions()
		self.validate_frequency()
	
	def validate_conditions(self):
		if self.conditions:
			try:
				conditions = json.loads(self.conditions)
				if not isinstance(conditions, dict):
					frappe.throw("Conditions must be a JSON object")
			except json.JSONDecodeError:
				frappe.throw("Invalid JSON format in conditions")
	
	def validate_frequency(self):
		if self.frequency in ["Weekly", "Monthly"] and not self.days_interval:
			frappe.throw(f"Days interval is required for frequency '{self.frequency}'", title="Validation Error", fieldname="days_interval")
	
	def enable_rule(self):
		"""Enable the SMS trigger rule"""
		self.is_active = 1
		self.save()
		frappe.msgprint(f"SMS Trigger Rule '{self.rule_name}' has been enabled")
	
	def disable_rule(self):
		"""Disable the SMS trigger rule"""
		self.is_active = 0
		self.save()
		frappe.msgprint(f"SMS Trigger Rule '{self.rule_name}' has been disabled")
	
	def can_execute(self):
		"""Check if rule can be executed based on frequency and last execution"""
		if not self.is_active:
			return False
		
		from frappe.utils import getdate, get_datetime
		
		# Check last execution
		if not self.last_execution:
			return True
		
		last_date = getdate(self.last_execution)
		today = getdate()
		
		if self.frequency == "Daily":
			return last_date < today
		elif self.frequency == "Weekly":
			return get_datetime(today).isocalendar()[1] != get_datetime(last_date).isocalendar()[1] or \
				   (today - last_date).days >= 7
		elif self.frequency == "Monthly":
			return today.month != last_date.month or today.year != last_date.year
		elif self.frequency == "One Time":
			# One time rules should not execute again
			return False
		
		return True
	
	def mark_executed(self):
		"""Mark rule as executed"""
		from frappe.utils import now_datetime
		self.last_execution = now_datetime()
		self.execution_count = (self.execution_count or 0) + 1
		self.save()