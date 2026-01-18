/*
* POS OTP Verification
* Intercepts POS payment submission to verify OTP for walking customers
*/

frappe.provide('sms_trigger.pos');

sms_trigger.pos.OTPController = class OTPController {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.verified_customers = []; // simple session cache
        this.init();
    }

    init() {
        console.log("POS OTP Controller Initialized");
        // Watch for POS payment submission
        // We'll try to monkey patch the POS payment submission
        // This is a bit hacky but standard for POS customizations

        const me = this;

        // Polling to wait for POS controller
        const interval = setInterval(() => {
            if (window.erpnext && window.erpnext.PointOfSale && window.erpnext.PointOfSale.Controller) {
                clearInterval(interval);
                me.patch_pos_controller();
            }
        }, 1000);
    }

    patch_pos_controller() {
        const me = this;
        const original_validate_invoice = erpnext.PointOfSale.Controller.prototype.validate_invoice;

        erpnext.PointOfSale.Controller.prototype.validate_invoice = function (doc) {
            const pos = this;

            // Return a promise to handle async verification
            return new Promise((resolve, reject) => {
                // Check if OTP needed
                me.check_otp_requirement(doc.customer, doc).then(required => {
                    if (!required) {
                        // Original flow
                        if (original_validate_invoice) {
                            // original_validate_invoice usually returns void or promise. 
                            // It modifies 'doc' or handles UI.
                            // Safest is to call it and resolve.
                            try {
                                const ret = original_validate_invoice.call(pos, doc);
                                resolve(ret);
                            } catch (e) {
                                reject(e);
                            }
                        } else {
                            resolve();
                        }
                        return;
                    }

                    // Check if already verified in this session
                    if (me.verified_customers.includes(doc.customer)) {
                        if (original_validate_invoice) {
                            try {
                                const ret = original_validate_invoice.call(pos, doc);
                                resolve(ret);
                            } catch (e) {
                                reject(e);
                            }
                        } else {
                            resolve();
                        }
                        return;
                    }

                    // Prompt for OTP
                    me.show_otp_dialog(doc.customer).then(success => {
                        if (success) {
                            me.verified_customers.push(doc.customer);
                            if (original_validate_invoice) {
                                try {
                                    const ret = original_validate_invoice.call(pos, doc);
                                    resolve(ret);
                                } catch (e) {
                                    reject(e);
                                }
                            } else {
                                resolve();
                            }
                        } else {
                            // Failed or Cancelled - verify rejects the promise or just stops
                            // Standard POS expects rejection to stop processing?
                            frappe.msgprint('OTP Verification Failed or Cancelled');
                            reject('OTP Verification Failed');
                        }
                    });
                });
            });
        };

        console.log("POS OTP: Patched validate_invoice");
    }

    check_otp_requirement(customer, doc) {
        return new Promise(resolve => {
            frappe.call({
                method: 'sms_trigger.sms_trigger.utils.pos_otp.check_otp_requirement',
                args: {
                    customer: customer,
                    grand_total: doc.grand_total,
                    discount_amount: doc.discount_amount || doc.base_discount_amount || 0
                    // We can add item level checks here if we parse items array and calculate sum
                },
                callback: function (r) {
                    resolve(r.message && r.message.required);
                }
            });
        });
    }

    show_otp_dialog(customer) {
        return new Promise(resolve => {
            const d = new frappe.ui.Dialog({
                title: 'Verify Customer Mobile OTP',
                fields: [
                    {
                        fieldname: 'info_html',
                        fieldtype: 'HTML',
                        options: `<div class="text-center text-muted">
                            <p>Verification required for <b>${customer}</b></p>
                            <p>Click generic 'Send OTP' to SMS the code.</p>
                        </div>`
                    },
                    {
                        label: 'OTP Code',
                        fieldname: 'otp',
                        fieldtype: 'Data',
                        reqd: 1
                    },
                    {
                        fieldname: 'send_btn',
                        fieldtype: 'Button',
                        label: 'Send OTP via SMS',
                        click: () => {
                            d.get_field('send_btn').input.disabled = true;
                            frappe.call({
                                method: 'sms_trigger.sms_trigger.utils.pos_otp.send_otp',
                                args: { customer: customer },
                                callback: (r) => {
                                    if (r.message && r.message.success) {
                                        frappe.msgprint(`OTP Sent! Expries in ${r.message.expiry} minutes.`);
                                    } else {
                                        frappe.msgprint(r.message.error || 'Failed to send OTP');
                                        d.get_field('send_btn').input.disabled = false;
                                    }
                                }
                            });
                        }
                    }
                ],
                primary_action_label: 'Verify & Proceed',
                primary_action: (values) => {
                    frappe.call({
                        method: 'sms_trigger.sms_trigger.utils.pos_otp.validate_otp',
                        args: {
                            customer: customer,
                            otp: values.otp
                        },
                        callback: (r) => {
                            if (r.message && r.message.success) {
                                d.hide();
                                resolve(true);
                            } else {
                                frappe.msgprint(r.message.error || 'Invalid OTP');
                            }
                        }
                    });
                }
            });
            d.show();
            d.onhide = () => {
                // If closed without verifying
                resolve(false);
            };
        });
    }
};

// Initialize
$(document).ready(function () {
    new sms_trigger.pos.OTPController();
});
