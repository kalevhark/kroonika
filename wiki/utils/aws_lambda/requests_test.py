from datetime import datetime, timedelta
import json
import logging

import boto3
import requests

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create an SNS client
sns = boto3.client('sns')

# Define the SNS topic ARN here
SNS_TOPIC_ARN = 'arn:aws:sns:eu-west-1:700227816743:valgalinnWebsiteUptimeNotifications'

urls = [
  'https://valgalinn.ee',
  'https://rfk.ee',
  'https://valgalinn.ee/wiki/objekt/68-vabaduse-68-s%C3%A4de-seltsimaja/'
]

def success_handler(msg, table, timestamp_string):
    # update table 'valgalinn_check_uptime'
    _ = table.update_item(
        Key={'success': 'yes'},
        UpdateExpression="SET timestamp_string = :s",
        ExpressionAttributeValues={
            ":s": timestamp_string,
        },
        ReturnValues="UPDATED_NEW",
    )
    _ = table.update_item(
        Key={'success': 'no'},
        UpdateExpression="SET counts = :n",
        ExpressionAttributeValues={
            ":n": 0
        },
        ReturnValues="UPDATED_NEW",
    )
    logger.info(msg)  # Log statement
    return {
        'statusCode': 200,
        'body': json.dumps(msg)
    }

def error_handler(msg, table, timestamp_string):
    # checktime
    timestamp = datetime.fromisoformat(timestamp_string)

    # get last success=no checktime
    response = table.get_item(Key={'success': 'no'})
    last_success_no_timestamp_string = response['Item']['timestamp_string']
    last_success_no_timestamp = datetime.fromisoformat(last_success_no_timestamp_string)
    if (timestamp - last_success_no_timestamp) < timedelta(seconds=120): # 2 minutes
        update_expression = "SET timestamp_string = :s, counts = counts + :n"
    else:
        update_expression = "SET timestamp_string = :s, counts = :n"

    # update table 'valgalinn_check_uptime'
    _ = table.update_item(
        Key={'success': 'no'},
        UpdateExpression=update_expression,
        ExpressionAttributeValues={
            ":s": timestamp_string,
            ":n": 1,
        },
        ReturnValues="UPDATED_NEW",
    )
    logger.error(msg)  # Log statement
    # If a URL error occurs (like the site is completely down), publish to SNS and log
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=f'{msg}',
        Subject=f'{msg}'
    )
    # mobile message:
    # sns.publish(
    #     PhoneNumber="+3725027768", Message=f"{msg}"
    # )
    return {
        'statusCode': 500,
        'body': json.dumps(msg)
    }

def lambda_handler(event, context):
    # checktime
    timestamp_string = datetime.now().isoformat()

    # Define the URL of your static website on S3
    url = 'https://valgalinn.ee'

    # Connect DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('valgalinn_check_uptime')

    try: 
        r = requests.head(url, timeout = 3, verify = True) 
        r.raise_for_status()
        msg = f'{url} is up.'
        response = success_handler(msg, table, timestamp_string)
    except requests.exceptions.HTTPError as err: 
        msg = f'{url}: {err.args[0]}'
        response = error_handler(msg, table, timestamp_string)
    except requests.exceptions.ReadTimeout as err: 
        msg = f'{url}: {err}'
        response = error_handler(msg, table, timestamp_string)
    except requests.exceptions.ConnectionError as err: 
        msg = f'{url}: {err}'
        response = error_handler(msg, table, timestamp_string)

    return response