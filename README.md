# SMS Trigger - ERPNext Custom App

Automatic SMS messaging system for ERPNext that sends SMS to customers based on configurable triggers and conditions.

## Features

- **Automated SMS Triggers**: Invoice due, birthdays, inactive customers, repurchase promotions
- **Configurable Rules**: Create custom SMS trigger rules with conditions
- **Scheduled SMS**: Queue and schedule SMS messages
- **SMS Gateway Integration**: Uses ERPNext's built-in SMS Settings
- **Reports & Dashboard**: Track SMS success rates and statistics
- **API Endpoints**: Programmatic SMS sending and management

## Installation

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/your-repo/sms_trigger --branch develop
bench install-app sms_trigger
bench migrate
```

## Setup

1. **Configure SMS Settings** (ERPNext > Settings > SMS Settings)
   - Set up your SMS gateway credentials
   - Test SMS functionality

2. **Create SMS Trigger Rules** (SMS Trigger > SMS Trigger Rule)
   - Define trigger conditions
   - Set message templates
   - Configure frequency and intervals

## Usage

### Trigger Types

- **Invoice Due**: Automatic reminders for overdue invoices
- **Birthday**: Birthday greetings to customers
- **Inactive Customer**: Re-engagement messages for inactive customers
- **Repurchase Promotion**: Promote repeat purchases of specific items
- **Customer Type/Group**: Target specific customer segments
- **Custom**: Manual SMS scheduling

### API Usage

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
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/sms_trigger
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


## Scheduler Jobs

- **Daily**: Process SMS trigger rules
- **Every 10 minutes**: Send pending SMS messages

## Reports

- **SMS Report**: View all scheduled, sent, and failed SMS with filters
- **SMS Success Rate Dashboard**: Visual analytics of SMS performance

## Extensibility

Add custom triggers by:
1. Creating new trigger types in SMS Trigger Rule
2. Adding processing logic in `trigger_engine.py`
3. Defining custom conditions in JSON format

## License

MIT
