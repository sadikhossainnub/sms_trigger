frappe.ui.form.on('Bulk SMS', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.status === "Draft" && frm.doc.total_recipients > 0 && !frm.is_new()) {
			frm.add_custom_button(__('Send Bulk SMS'), function() {
				frappe.confirm(
					__('Are you sure you want to send SMS to {0} recipients?', [frm.doc.total_recipients]),
					function() {
						frm.call('send_bulk_sms').then(() => {
							frm.reload_doc();
						});
					}
				);
			}, __('Actions'));
		}
		
		if (frm.doc.status === "Draft") {
			frm.add_custom_button(__('Load Recipients'), function() {
				frm.call('load_recipients').then(() => {
					frm.reload_doc();
				});
				}, __('Actions'));
		}
		
		// Add retry button for failed campaigns
		if (frm.doc.status === "Failed" || frm.doc.status === "Completed") {
			if (frm.doc.failed_count > 0) {
				frm.add_custom_button(__('Retry Failed SMS'), function() {
					frappe.confirm(
						__('Are you sure you want to retry {0} failed SMS?', [frm.doc.failed_count]),
						function() {
							frm.call('retry_failed_sms').then(() => {
								frm.reload_doc();
							});
						}
					);
				}, __('Actions'));
			}
		}
	},
	
	filter_by: function(frm) {
		frm.trigger('load_recipients');
	},
	
	
	customer_group: function(frm) {
		if (frm.doc.filter_by === "Customer Group") {
			frm.trigger('load_recipients');
		}
	},
	
	territory: function(frm) {
		if (frm.doc.filter_by === "Territory") {
			frm.trigger('load_recipients');
		}
	},
	
	gender: function(frm) {
		if (frm.doc.filter_by === "Gender") {
			frm.trigger('load_recipients');
		}
	},
	
	religion: function(frm) {
		if (frm.doc.filter_by === "Religion") {
			frm.trigger('load_recipients');
		}
	},
	
	profession: function(frm) {
		if (frm.doc.filter_by === "Profession") {
			frm.trigger('load_recipients');
		}
	},
	
	custom_filter: function(frm) {
		if (frm.doc.filter_by === "Custom Filter") {
			frm.trigger('load_recipients');
		}
	},
	
	load_recipients: function(frm) {
		if (frm.doc.filter_by) {
			frm.call('load_recipients').then(() => {
				frm.refresh_field('recipients');
				frm.refresh_field('total_recipients');
			});
		}
	},
	
	send_sms_button: function(frm) {
		frappe.confirm(
			__('Are you sure you want to send SMS to {0} recipients?', [frm.doc.total_recipients]),
			function() {
				frm.call('send_bulk_sms').then(() => {
					frm.reload_doc();
				});
			}
		);
	}
});

// Real-time progress updates
frappe.realtime.on('bulk_sms_progress', function(data) {
	if (cur_frm && cur_frm.doc.doctype === 'Bulk SMS') {
		cur_frm.reload_doc();
	}
});

frappe.realtime.on('bulk_sms_completed', function(data) {
	if (cur_frm && cur_frm.doc.doctype === 'Bulk SMS') {
		cur_frm.reload_doc();
		frappe.show_alert({
			message: __('Bulk SMS completed: {0} success, {1} failed', [data.success, data.failed]),
			indicator: 'green'
		});
	}
});