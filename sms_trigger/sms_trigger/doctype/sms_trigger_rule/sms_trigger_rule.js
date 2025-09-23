frappe.ui.form.on('SMS Trigger Rule', {
	refresh: function(frm) {
		// Add custom buttons
		if (!frm.doc.__islocal) {
			// Toggle button
			if (frm.doc.is_active) {
				frm.add_custom_button(__('Disable Rule'), function() {
					disable_rule(frm);
				}, __('Actions'));
			} else {
				frm.add_custom_button(__('Enable Rule'), function() {
					enable_rule(frm);
				}, __('Actions'));
			}
			
			// Test rule button
			frm.add_custom_button(__('Test Rule'), function() {
				test_rule(frm);
			}, __('Actions'));
			
			// Validate conditions button
			if (frm.doc.conditions) {
				frm.add_custom_button(__('Validate Conditions'), function() {
					validate_conditions(frm);
				}, __('Actions'));
			}
		}
		
		// Set field descriptions
		frm.set_df_property('conditions', 'description', 
			'Enter JSON conditions. Example: {"customer_type": "Individual", "customer_group": "All Customer Groups"}');
		frm.set_df_property('frequency', 'description', 
			'How often this rule should run. One Time rules run only once per customer.');
		frm.set_df_property('days_interval', 'description', 
			'For Invoice Due: days overdue. For Inactive Customer: days since last purchase. For Repurchase: days since last purchase of item.');
	},
	
	trigger_type: function(frm) {
		// Set default conditions based on trigger type
		if (frm.doc.trigger_type && !frm.doc.conditions) {
			let default_conditions = get_default_conditions(frm.doc.trigger_type);
			if (default_conditions) {
				frm.set_value('conditions', JSON.stringify(default_conditions, null, 2));
			}
		}
		
		// Set default message template
		if (frm.doc.trigger_type && !frm.doc.message_template) {
			let default_message = get_default_message(frm.doc.trigger_type);
			if (default_message) {
				frm.set_value('message_template', default_message);
			}
		}
	},
	
	conditions: function(frm) {
		// Validate JSON on change
		if (frm.doc.conditions) {
			try {
				JSON.parse(frm.doc.conditions);
				frm.set_df_property('conditions', 'description', 'Valid JSON conditions');
			} catch (e) {
				frm.set_df_property('conditions', 'description', 'Invalid JSON: ' + e.message);
			}
		}
	}
});

function enable_rule(frm) {
	frappe.call({
		method: 'sms_trigger.sms_trigger.api.enable_sms_rule',
		args: {
			rule_name: frm.doc.name
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				frappe.msgprint(r.message.message);
				frm.reload_doc();
			}
		}
	});
}

function disable_rule(frm) {
	frappe.confirm(
		'Are you sure you want to disable this SMS rule?',
		function() {
			frappe.call({
				method: 'sms_trigger.sms_trigger.api.disable_sms_rule',
				args: {
					rule_name: frm.doc.name
				},
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.msgprint(r.message.message);
						frm.reload_doc();
					}
				}
			});
		}
	);
}

function test_rule(frm) {
	let d = new frappe.ui.Dialog({
		title: 'Test SMS Rule',
		fields: [
			{
				label: 'Test Customer',
				fieldname: 'customer',
				fieldtype: 'Link',
				options: 'Customer',
				description: 'Leave empty to use first customer with mobile number'
			}
		],
		primary_action_label: 'Send Test SMS',
		primary_action(values) {
			frappe.call({
				method: 'sms_trigger.sms_trigger.api.test_sms_rule',
				args: {
					rule_name: frm.doc.name,
					test_customer: values.customer
				},
				callback: function(r) {
					if (r.message) {
						if (r.message.success) {
							frappe.msgprint(`Test SMS sent successfully to ${r.message.customer} (${r.message.mobile_no})<br>Message: ${r.message.message}`);
						} else {
							frappe.msgprint(`Test failed: ${r.message.error}`);
						}
					}
					d.hide();
				}
			});
		}
	});
	d.show();
}

function validate_conditions(frm) {
	frappe.call({
		method: 'sms_trigger.sms_trigger.api.validate_sms_conditions',
		args: {
			conditions: frm.doc.conditions
		},
		callback: function(r) {
			if (r.message) {
				if (r.message.valid) {
					frappe.msgprint('Conditions are valid JSON');
				} else {
					frappe.msgprint('Invalid conditions: ' + r.message.error);
				}
			}
		}
	});
}

function get_default_conditions(trigger_type) {
	const defaults = {
		'Customer Type': {"customer_type": "Individual"},
		'Customer Group': {"customer_group": "All Customer Groups"},
		'Repurchase Promotion': {"item_code": "ITEM-001"}
	};
	return defaults[trigger_type];
}

function get_default_message(trigger_type) {
	const messages = {
		'Invoice Due': 'Dear {customer_name}, your invoice {invoice_no} of amount {amount} is overdue. Please make payment at your earliest convenience.',
		'Birthday': 'Happy Birthday {customer_name}! Wishing you a wonderful day filled with joy and happiness.',
		'Inactive Customer': 'Hi {customer_name}, we miss you! Come back and explore our latest offers.',
		'Repurchase Promotion': 'Hi {customer_name}, time to reorder {item_code}! Special discount available.',
		'Customer Type': 'Dear {customer_name}, we have special offers just for you!',
		'Customer Group': 'Hello {customer_name}, exclusive deals for our valued customers!'
	};
	return messages[trigger_type];
}