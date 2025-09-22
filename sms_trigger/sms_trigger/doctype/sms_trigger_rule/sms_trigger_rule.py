import frappe
from frappe.model.document import Document

class SMSTriggerRule(Document):
	def validate(self):
		if self.conditions:
			try:
				import json
				json.loads(self.conditions)
			except:
				frappe.throw("Invalid JSON format in conditions")