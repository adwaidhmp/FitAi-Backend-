# Premium Expired Email Lambda

This AWS Lambda function is triggered by SQS messages
sent from the Django Celery task.

## Trigger
- AWS SQS: premium-expired-email-queue

## Expected Message Format
```json
{
  "email": "user@example.com"
}
