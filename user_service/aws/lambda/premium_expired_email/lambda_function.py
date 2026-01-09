import json
import boto3
import os

ses = boto3.client("ses")

def lambda_handler(event, context):
    """
    Triggered by SQS
    Message format:
    {
        "email": "user@gmail.com"
    }
    """

    for record in event["Records"]:
        body = json.loads(record["body"])
        email = body.get("email")

        if not email:
            continue

        ses.send_email(
            Source=os.environ["FROM_EMAIL"],
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {
                    "Data": "Your Premium Plan Has Expired",
                    "Charset": "UTF-8",
                },
                "Body": {
                    "Text": {
                        "Data": (
                            "Hi,\n\n"
                            "Your premium subscription has expired.\n"
                            "Please renew to continue premium features.\n\n"
                            "— Team"
                        ),
                        "Charset": "UTF-8",
                    }
                },
            },
        )

    return {"statusCode": 200}