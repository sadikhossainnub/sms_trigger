frappe.ui.form.on('Bulk SMS', {
	refresh: function (frm) {
		if (frm.doc.docstatus === 1 && (frm.doc.status === 'Failed' || (frm.doc.status === 'Completed' && frm.doc.failed_count > 0))) {
			frm.add_custom_button(__('Retry Failed SMS'), function () {
				frm.call('retry_failed_sms');
			});
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__('Load Recipients'), function () {
				frm.trigger('load_recipients');
			});

			if (frm.doc.total_recipients > 0) {
				frm.add_custom_button(__('Sent'), function () {
					frm.submit();
				}).addClass('btn-primary');
			}
		}

		if (!frm.is_new()) {
			frappe.realtime.on("bulk_sms_progress", function (data) {
				frm.reload_doc();
			});

			frappe.realtime.on("bulk_sms_completed", function (data) {
				frm.reload_doc();
			});
		}
	},

	filter_by: function (frm) {
		if (frm.doc.docstatus === 0) {
			frm.trigger('load_recipients');
		}
	},

	customer_group: function (frm) {
		if (frm.doc.docstatus === 0) {
			frm.trigger('load_recipients');
		}
	},

	territory: function (frm) {
		if (frm.doc.docstatus === 0) {
			frm.trigger('load_recipients');
		}
	},

	load_recipients: function (frm) {
		frm.call({
			method: 'load_recipients',
			doc: frm.doc,
			callback: function (r) {
				if (r.message) {
					frm.clear_table('recipients');
					r.message.forEach(function (d) {
						let row = frm.add_child('recipients');
						row.customer = d.customer;
						row.customer_name = d.customer_name;
						row.mobile_no = d.mobile_no;
						row.status = d.status;
					});
					frm.refresh_field('recipients');
					frm.set_value('total_recipients', r.message.length);
				}
			}
		});
	}
});