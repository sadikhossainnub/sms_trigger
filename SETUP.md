# SMS Trigger - Complete Setup Guide

## Prerequisites

1. **ERPNext Installation**: Ensure ERPNext is properly installed and running
2. **SMS Gateway**: Configure SMS Settings in ERPNext with your SMS provider
3. **Python Dependencies**: All required dependencies are included with ERPNext

## Installation Steps

### 1. Install the App

```bash
# Navigate to your bench directory
cd /path/to/your/bench

# Get the app from repository
bench get-app https://github.com/your-repo/sms_trigger --branch main

# Install the app to your site
bench --site your-site.local install-app sms_trigger

# Migrate the database
bench --site your-site.local migrate

# Restart bench
bench restart
```

### 2. Configure SMS Settings

1. Go to **Settings > SMS Settings**
2. Configure your SMS gateway:
   - **SMS Gateway URL**: Your SMS provider's API endpoint
   - **Parameters**: Required parameters for your SMS provider
   - **Username/Password**: Your SMS gateway credentials

3. Test SMS functionality:
   ```bash
   # Test SMS from bench console
   bench --site your-site.local console
   
   # In the console:
   from sms_trigger.sms_trigger.utils.sms_gateway import test_sms_gateway
   test_sms_gateway("+1234567890", "Test message")
   ```

### 3. Initial Configuration

1. **Enable SMS for Customers**:
   - The app automatically adds an "SMS Enabled" field to Customer doctype
   - By default, all customers have SMS enabled

2. **Set Customer Birth Dates** (for birthday SMS):
   - Add birth dates to customer records for birthday triggers

3. **Review Default Rules**:
   - The app creates default SMS trigger rules
   - Review and customize them in **SMS > SMS Trigger Rule**

## Configuration Guide

### SMS Trigger Rules

#### Rule Types Available:

1. **Invoice Due**: Send reminders for overdue invoices
2. **Birthday**: Send birthday wishes to customers
3. **Inactive Customer**: Re-engage inactive customers
4. **Repurchase Promotion**: Promote repeat purchases
5. **Customer Type**: Target specific customer types
6. **Customer Group**: Target specific customer groups

#### Creating Custom Rules:

```json
// Example conditions for Customer Type rule
{
  "customer_type": "Individual",
  "territory": "India"
}

// Example conditions for Repurchase Promotion
{
  "item_code": "ITEM-001",
  "min_purchase_amount": 1000
}
```

#### Message Templates:

Use Jinja2 templating for dynamic content:

```html
<!-- Invoice Due Template -->
Dear {{ customer_name }}, 
Your invoice {{ invoice_no }} for {{ amount }} is overdue. 
Please make payment by {{ due_date }}.

<!-- Birthday Template -->
Happy Birthday {{ customer_name }}! 
Enjoy 20% off your next purchase with code BIRTHDAY20.

<!-- Inactive Customer Template -->
Hi {{ customer_name }}, 
We miss you! Here's a special 15% discount: COMEBACK15
```

### Frequency Settings:

- **Daily**: Execute every day
- **Weekly**: Execute once per week
- **Monthly**: Execute once per month
- **One Time**: Execute only once

### Advanced Configuration

#### Rate Limiting:
- Built-in rate limiting: 5 SMS per hour per mobile number
- Prevents spam and reduces costs

#### Error Handling:
- Automatic retry mechanism with exponential backoff
- Rules auto-disable after 5 consecutive errors
- Comprehensive error logging

#### Cleanup:
- Automatic cleanup of old SMS logs (90+ days)
- Prevents database bloat

## API Usage

### Programmatic SMS Sending

```python
# Schedule SMS
frappe.call("sms_trigger.sms_trigger.api.schedule_sms", {
    "customer": "CUST-001",
    "message": "Your order is ready for pickup!"
})

# Send immediate SMS
frappe.call("sms_trigger.sms_trigger.api.send_immediate_sms", {
    "customer": "CUST-001", 
    "message": "Urgent: Please contact us immediately."
})

# Get SMS statistics
stats = frappe.call("sms_trigger.sms_trigger.api.get_sms_stats", {
    "from_date": "2024-01-01",
    "to_date": "2024-01-31"
})
```

### REST API Endpoints

```bash
# Create SMS rule
curl -X POST "https://your-site.local/api/method/sms_trigger.sms_trigger.api.create_sms_trigger_rule" \
  -H "Authorization: token api_key:api_secret" \
  -d '{
    "rule_name": "New Customer Welcome",
    "trigger_type": "Custom",
    "message_template": "Welcome {{ customer_name }}!",
    "frequency": "One Time"
  }'

# Get SMS statistics
curl "https://your-site.local/api/method/sms_trigger.sms_trigger.api.get_sms_stats" \
  -H "Authorization: token api_key:api_secret"
```

## Monitoring and Maintenance

### Health Check

```python
# Check system health
frappe.call("sms_trigger.sms_trigger.utils.error_handler.get_sms_health_check")
```

### Performance Monitoring

1. **SMS Success Rate**: Monitor in SMS Report
2. **Rule Performance**: Check execution counts and success rates
3. **Error Logs**: Review failed SMS and trigger errors

### Maintenance Tasks

```bash
# Manual trigger processing
bench --site your-site.local execute sms_trigger.sms_trigger.utils.trigger_engine.process_sms_triggers

# Send pending SMS
bench --site your-site.local execute sms_trigger.sms_trigger.utils.trigger_engine.send_pending_sms

# Cleanup old logs
bench --site your-site.local execute sms_trigger.sms_trigger.utils.trigger_engine.cleanup_old_logs
```

## Troubleshooting

### Common Issues

1. **SMS Not Sending**:
   - Check SMS Settings configuration
   - Verify SMS gateway credentials
   - Check customer mobile numbers

2. **Rules Not Executing**:
   - Verify rule is active
   - Check frequency settings
   - Review error logs

3. **High Error Rate**:
   - Check SMS gateway status
   - Verify mobile number formats
   - Review rate limiting

### Debug Mode

```python
# Enable debug logging
frappe.conf.developer_mode = 1

# Check SMS queue
frappe.get_all("Scheduled SMS", {"status": "Draft"})

# Test rule execution
from sms_trigger.sms_trigger.utils.trigger_engine import process_trigger_rule
rule = frappe.get_doc("SMS Trigger Rule", "rule-name")
process_trigger_rule(rule)
```

### Performance Optimization

1. **Batch Processing**: SMS are processed in batches of 100
2. **Rate Limiting**: Prevents API overload
3. **Cleanup Jobs**: Automatic cleanup prevents database bloat
4. **Error Handling**: Failed rules are auto-disabled

## Security Considerations

1. **API Access**: Use proper authentication for API calls
2. **Mobile Number Validation**: Built-in validation prevents invalid numbers
3. **Message Length**: Automatic truncation prevents oversized messages
4. **Rate Limiting**: Prevents abuse and spam

## Support and Maintenance

### Regular Maintenance:
- Monitor SMS success rates weekly
- Review and update message templates monthly
- Check error logs regularly
- Update customer mobile numbers as needed

### Backup Considerations:
- SMS logs are included in regular ERPNext backups
- Consider archiving old SMS data periodically

### Scaling:
- The app handles high-volume SMS efficiently
- Consider SMS gateway limits and pricing
- Monitor database growth with SMS logs

## Integration Examples

### Custom Triggers

```python
# Custom trigger in your app
def create_welcome_sms(doc, method):
    """Send welcome SMS when customer is created"""
    if doc.mobile_no:
        frappe.call("sms_trigger.sms_trigger.api.schedule_sms", {
            "customer": doc.name,
            "message": f"Welcome {doc.customer_name}! Thank you for joining us.",
            "trigger_type": "Custom"
        })

# Add to hooks.py
doc_events = {
    "Customer": {
        "after_insert": "your_app.utils.create_welcome_sms"
    }
}
```

### Webhook Integration

```python
# Webhook for external SMS triggers
@frappe.whitelist(allow_guest=True)
def webhook_sms_trigger():
    data = frappe.local.form_dict
    
    # Validate webhook
    if not validate_webhook_signature(data):
        frappe.throw("Invalid webhook signature")
    
    # Process SMS request
    return frappe.call("sms_trigger.sms_trigger.api.send_immediate_sms", {
        "customer": data.get("customer"),
        "message": data.get("message")
    })
```

This comprehensive setup ensures your SMS Trigger app is robust, automated, and production-ready.