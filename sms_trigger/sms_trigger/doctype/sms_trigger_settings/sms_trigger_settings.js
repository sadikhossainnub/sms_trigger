frappe.ui.form.on('SMS Trigger Settings', {
	pos_sms_template: function(frm) {
		if (frm.doc.pos_sms_template) {
			frappe.call({
				method: 'sms_trigger.sms_trigger.utils.pos_sms.get_pos_sms_preview',
				args: {
					template: frm.doc.pos_sms_template
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: 'SMS Preview',
							message: '<strong>Preview:</strong><br><div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">' + r.message + '</div>',
							indicator: 'blue'
						});
					}
				}
			});
		}
	}
});