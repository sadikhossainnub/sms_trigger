# SMS Trigger - ERPNext Custom App

🚀 **Production-Ready** | 📱 **Fully Automated** | 🔧 **Highly Configurable**

A robust, enterprise-grade SMS messaging system for ERPNext that automatically sends SMS to customers based on intelligent triggers and conditions.

## ✨ Key Features

- **🤖 Fully Automated SMS Triggers**: Invoice due, birthdays, inactive customers, repurchase promotions
- **⚙️ Advanced Rule Engine**: Create complex SMS trigger rules with JSON conditions
- **📅 Smart Scheduling**: Queue and schedule SMS messages with frequency controls
- **🔗 SMS Gateway Integration**: Seamless integration with ERPNext's SMS Settings
- **📊 Analytics Dashboard**: Comprehensive SMS performance tracking and reporting
- **🔌 REST API**: Full programmatic control via API endpoints
- **🛡️ Error Handling**: Robust error handling with automatic retry mechanisms
- **📈 Rate Limiting**: Built-in rate limiting to prevent spam and control costs
- **🔍 Health Monitoring**: Real-time system health checks and performance monitoring
- **🧹 Auto Cleanup**: Automatic cleanup of old logs to prevent database bloat

## 🚀 Quick Installation

```bash
# Navigate to your bench directory
cd /path/to/your/bench

# Install the app
bench get-app https://github.com/your-repo/sms_trigger --branch main
bench --site your-site.local install-app sms_trigger
bench --site your-site.local migrate
bench restart

# Verify installation
bench --site your-site.local console
>>> frappe.call("sms_trigger.sms_trigger.utils.validation.validate_app_installation")
```

📖 **For detailed setup instructions, see [SETUP.md](SETUP.md)**

## ⚡ Quick Setup

### 1. Configure SMS Gateway
```bash
# Go to Settings > SMS Settings in ERPNext
# Configure your SMS provider credentials
# Test with: frappe.call("sms_trigger.sms_trigger.utils.sms_gateway.test_sms_gateway", {"mobile_no": "+1234567890"})
```

### 2. Review Default Rules
The app automatically creates optimized default rules:
- ✅ **Invoice Due Reminder** (7 days overdue)
- 🎂 **Birthday Wishes** (daily check)
- 💤 **Inactive Customer Follow-up** (90+ days inactive)

### 3. Customize & Activate
- Navigate to **SMS > SMS Trigger Rule**
- Customize message templates
- Activate rules as needed
- Monitor performance in **SMS > SMS Report**

## 🎯 Advanced Usage

### Intelligent Trigger Types

| Trigger Type | Description | Use Case |
|--------------|-------------|----------|
| 📄 **Invoice Due** | Automatic overdue reminders | Improve cash flow |
| 🎂 **Birthday** | Personalized birthday wishes | Customer retention |
| 💤 **Inactive Customer** | Re-engagement campaigns | Win back customers |
| 🛒 **Repurchase Promotion** | Item-specific promotions | Increase repeat sales |
| 👥 **Customer Type/Group** | Segment-based messaging | Targeted marketing |
| ⚡ **Custom** | Manual/API triggered | Event-based messaging |

### Smart Conditions (JSON)
```json
// Target high-value inactive customers
{
  "customer_type": "Company",
  "territory": "India",
  "last_purchase_amount": {">=": 10000}
}

// Birthday promotion for VIP customers
{
  "customer_group": "VIP",
  "sms_enabled": 1
}
```

### 🔌 Powerful API

```python
# Schedule SMS with advanced options
frappe.call("sms_trigger.sms_trigger.api.schedule_sms", {
    "customer": "CUST-001",
    "message": "Your order #{{ order_no }} is ready!",
    "scheduled_datetime": "2024-01-15 10:00:00",
    "trigger_type": "Order Ready"
})

# Bulk operations
frappe.call("sms_trigger.sms_trigger.api.create_bulk_sms", {
    "campaign_name": "New Year Sale",
    "message": "🎉 New Year Sale: 50% OFF! Use code: NY2024",
    "filter_by": "Customer Group",
    "customer_group": "Retail"
})

# Get comprehensive analytics
stats = frappe.call("sms_trigger.sms_trigger.api.get_sms_stats", {
    "from_date": "2024-01-01",
    "to_date": "2024-01-31"
})
print(f"Success Rate: {stats['success_rate']}%")

# Health monitoring
health = frappe.call("sms_trigger.sms_trigger.utils.error_handler.get_sms_health_check")
print(f"System Status: {health['health']['overall_status']}")
```

### 🔄 Continuous Integration

**GitHub Actions Workflows:**
- ✅ **CI Pipeline**: Automated testing on every push
- 🔍 **Code Quality**: Frappe Semgrep Rules + pip-audit
- 🚀 **Auto Deploy**: Automated deployment to staging/production
- 📊 **Performance Tests**: Load testing for high-volume scenarios


## ⏰ Automated Scheduler Jobs

| Frequency | Job | Purpose |
|-----------|-----|----------|
| 📅 **Daily** | Process SMS trigger rules | Execute all active rules |
| ⚡ **Every 10 min** | Send pending SMS | Deliver queued messages |
| 🧹 **Hourly** | Cleanup old logs | Maintain database performance |

### Manual Execution
```bash
# Force trigger processing
bench --site your-site.local execute sms_trigger.sms_trigger.utils.trigger_engine.process_sms_triggers

# Send pending SMS immediately  
bench --site your-site.local execute sms_trigger.sms_trigger.utils.trigger_engine.send_pending_sms
```

## 📊 Advanced Analytics & Monitoring

### Built-in Reports
- 📈 **SMS Performance Dashboard**: Real-time success rates and trends
- 📋 **Detailed SMS Report**: Filterable view of all SMS activities
- 🎯 **Rule Performance Analysis**: Individual rule effectiveness metrics
- ⚠️ **Error Analysis Report**: Failed SMS investigation and resolution

### Health Monitoring
```python
# System health check
health = frappe.call("sms_trigger.sms_trigger.utils.error_handler.get_sms_health_check")

# Rule performance metrics
performance = frappe.call("sms_trigger.sms_trigger.api.get_trigger_rule_performance")

# Customer SMS history
history = frappe.call("sms_trigger.sms_trigger.api.get_customer_sms_history", {
    "customer": "CUST-001",
    "limit": 50
})
```

## 🔧 Enterprise Features

### Advanced Error Handling
- ✅ **Automatic Retry**: Exponential backoff for failed SMS
- 🛡️ **Rate Limiting**: 5 SMS/hour per number (configurable)
- 📊 **Error Analytics**: Comprehensive failure analysis
- 🔄 **Auto-Recovery**: Rules auto-disable after 5 consecutive errors

### Performance Optimization
- ⚡ **Batch Processing**: Handle high-volume SMS efficiently
- 🧹 **Auto Cleanup**: Remove logs older than 90 days
- 📈 **Smart Caching**: Optimized database queries
- 🔍 **Health Monitoring**: Real-time system status

### Security & Compliance
- 🔒 **Mobile Validation**: Automatic number format validation
- 🚫 **Spam Prevention**: Built-in rate limiting and duplicate detection
- 📝 **Audit Trail**: Complete SMS activity logging
- 🛡️ **Permission Control**: Role-based access to SMS features

### Extensibility
```python
# Custom trigger example
def process_custom_trigger(rule):
    # Your custom logic here
    customers = get_customers_by_custom_criteria(rule.conditions)
    for customer in customers:
        create_scheduled_sms(
            customer=customer.name,
            message=render_template(rule.message_template, customer),
            trigger_type="Custom Event"
        )
```

## 🤝 Support & Contributing

### Getting Help
- 📖 **Documentation**: See [SETUP.md](SETUP.md) for detailed setup
- 🐛 **Issues**: Report bugs via GitHub Issues
- 💬 **Discussions**: Join our community discussions
- 📧 **Support**: Contact support for enterprise assistance

### System Validation
```python
# Validate installation
frappe.call("sms_trigger.sms_trigger.utils.validation.validate_app_installation")

# Run system tests
frappe.call("sms_trigger.sms_trigger.utils.validation.run_system_test")

# Get system info
frappe.call("sms_trigger.sms_trigger.utils.validation.get_system_info")
```

### Contributing
This app uses `pre-commit` for code quality:

```bash
cd apps/sms_trigger
pre-commit install
```

**Tools used**: ruff, eslint, prettier, pyupgrade

---

## 📄 License

**MIT License** - Feel free to use in commercial projects

---

**⭐ Star this repo if it helps your business!**

*Built with ❤️ for the ERPNext community*
