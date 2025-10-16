frappe.ui.form.on('Bulk SMS', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && (frm.doc.status === 'Failed' || (frm.doc.status === 'Completed' && frm.doc.failed_count > 0))) {
			frm.add_custom_button(__('Retry Failed SMS'), function() {
				frm.call('retry_failed_sms');
			});
		}
		
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Load Recipients'), function() {
				frm.call('load_recipients');
			});
		}
	},
	
	filter_by: function(frm) {
		if (frm.doc.docstatus === 0) {
			frm.call('load_recipients');
		}
	},
	
	customer_group: function(frm) {
		if (frm.doc.docstatus === 0) {
			frm.call('load_recipients');
		}
	},
	
	territory: function(frm) {
		if (frm.doc.docstatus === 0) {
			frm.call('load_recipients');
		}
	}
});