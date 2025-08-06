# Email Notification Configuration

## Overview
The data-collection workflow supports optional email notifications for collection status updates. Email notifications are **optional** and the workflow will complete successfully without them.

## Required GitHub Secrets

To enable email notifications, configure these secrets in your GitHub repository:

### Repository Settings → Secrets and variables → Actions → Environment secrets → production

```yaml
EMAIL_ENABLED: "true"                    # Set to "true" to enable email notifications
SMTP_HOST: "smtp.gmail.com"              # Your SMTP server (Gmail example)
SMTP_PORT: "587"                         # SMTP port (default: 587)
SMTP_USERNAME: "your-email@gmail.com"    # SMTP username
SMTP_PASSWORD: "your-app-password"       # App password for Gmail (not regular password)
SENDER_EMAIL: "your-email@gmail.com"     # From email address
RECIPIENT_EMAILS: "user1@domain.com,user2@domain.com"  # Comma-separated recipients
```

## Email Providers Configuration

### Gmail Configuration
1. Enable 2-Factor Authentication on your Gmail account
2. Generate an App Password: 
   - Go to Google Account Settings → Security → 2-Step Verification → App passwords
   - Generate a password for "Mail"
   - Use this app password as `SMTP_PASSWORD`
3. Use these settings:
   - `SMTP_HOST`: smtp.gmail.com
   - `SMTP_PORT`: 587

### Outlook/Hotmail Configuration
```yaml
SMTP_HOST: "smtp-mail.outlook.com"
SMTP_PORT: "587"
SMTP_USERNAME: "your-email@outlook.com"
SMTP_PASSWORD: "your-password"
```

### Other SMTP Providers
Most SMTP providers work with these settings. Check your provider's documentation for specific SMTP configuration.

## Email Content

The workflow sends different types of emails based on collection status:

- **Success**: Collection completed successfully
- **Warning**: Partial success (some components failed)
- **Error**: Complete collection failure

Each email includes:
- Collection timestamp and status
- Component status (Maricopa API, Phoenix MLS, LLM Processing, Validation)
- ZIP codes processed
- Collection mode used
- GitHub Actions run URL for detailed logs

## Disabling Email Notifications

Email notifications are disabled by default. To explicitly disable:
- Set `EMAIL_ENABLED` to `"false"` or remove the secret entirely
- The workflow will log: `[INFO] Email service not configured, skipping email notification`

## Troubleshooting

### Common Issues:
1. **Authentication Failed**: Check SMTP username/password and use app passwords for Gmail
2. **Connection Timeout**: Verify SMTP host and port settings
3. **SSL/TLS Issues**: Most providers use STARTTLS on port 587

### Testing Email Configuration:
The email sending logic only executes when all required secrets are configured. Test by:
1. Configuring all required secrets
2. Running the workflow manually
3. Checking workflow logs for email delivery confirmation

## Security Notes

- Never commit email credentials to the repository
- Use App Passwords instead of main account passwords where available
- Regularly rotate SMTP passwords
- Monitor email sending logs for unauthorized usage
EOF < /dev/null
