# lambda_function.py
#
# Check valgalinn.ee uptime in every 5 minutes:
# Amazon EventBridge: arn:aws:scheduler:eu-west-1:700227816743:schedule/default/rulevalgalinnWebsiteUptimeNotifications

from datetime import datetime
import json
import urllib.request
from urllib.error import URLError, HTTPError
import boto3
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define the SNS topic ARN here
SNS_TOPIC_ARN = 'arn:aws:sns:eu-west-1:700227816743:valgalinnWebsiteUptimeNotifications'


def lambda_handler(event, context):
    # checktime
    timestamp_string = datetime.now().isoformat()

    # Define the URL of your static website on S3
    website_url = 'https://valgalinn.ee'

    # Create an SNS client
    sns = boto3.client('sns')

    # Connect DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('valgalinn_check_uptime')

    try:
        # Try to retrieve the website URL
        response = urllib.request.urlopen(website_url, timeout=10)
        # If the response status code is 200, the website is up
        if response.getcode() == 200:
            # update table 'valgalinn_check_uptime'
            _ = table.update_item(
                Key={'success': 'yes'},
                UpdateExpression="SET timestamp_string = :s",
                ExpressionAttributeValues={
                    ":s": timestamp_string,
                },
                ReturnValues="UPDATED_NEW",
            )
            logger.info('Website is up.')  # Log statement
            return {
                'statusCode': 200,
                'body': json.dumps('Website is up.')
            }
        # else:
        # logger.warning('Website is up, but returned a non-200 status code.')  # Log statement
        # You might want to handle non-200 status codes here
    except HTTPError as e:
        # update table 'valgalinn_check_uptime'
        _ = table.update_item(
            Key={'success': 'no'},
            UpdateExpression="SET timestamp_string = :s, counts = counts + :n",
            ExpressionAttributeValues={
                ":s": timestamp_string,
                ":n": 1,
            },
            ReturnValues="UPDATED_NEW",
        )
        # If a HTTP error occurs (like a 5xx response), publish to SNS and log
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message='Your website returned a server error: ' + str(e.code),
            Subject='Website Down Alert'
        )
        logger.error('HTTPError: ' + str(e.code))  # Log statement
        return {
            'statusCode': e.code,
            'body': json.dumps('Website is down!')
        }
    except URLError as e:
        # update table 'valgalinn_check_uptime'
        _ = table.update_item(
            Key={'success': 'no'},
            UpdateExpression="SET timestamp_string = :s, counts = counts + :n",
            ExpressionAttributeValues={
                ":s": timestamp_string,
                ":n": 1,
            },
            ReturnValues="UPDATED_NEW",
        )
        # If a URL error occurs (like the site is completely down), publish to SNS and log
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message='Your website is down: ' + str(e.reason),
            Subject='Website Down Alert'
        )
        logger.error('URLError: ' + str(e.reason))  # Log statement

    # This will only be reached if an exception is not caught
    # logger.error('Website is down!')

    # mobile message:
    # sns.publish(
    #     PhoneNumber="+3725027768", Message="test 09:02"
    # )

    # check fail count:
    # response = table.get_item(Key={'success': 'no'})
    # response['Item']
    # > {'counts': Decimal('0'), 'success': 'no', 'timestamp_string': ''}
    # response['Item']['counts'] % 5 == 0
