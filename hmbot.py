import json, re, requests, os, sys, logging

logging.basicConfig()
logger = logging.getLogger('hmbot')
logger.setLevel(logging.INFO)

from slackclient import SlackClient
sc = SlackClient(os.environ['SLACK_TOKEN'])

def lambda_handler(event, context):
    body = event['body']
    slack_msg = json.loads(body)
    event_type = slack_msg['type']
    
    if event_type == u'url_verification':
        return {
            'statusCode': 200,
            'body': slack_event['challenge']
        }
    else:
        try:
            handle_msg(slack_msg)
        except:
            logger.error("error handling slack message", exc_info=True)

        return {
            'statusCode': 200,
            'body': ''
        }

def handle_msg(slack_msg):
    if 'event' not in slack_msg: return

    logger.info("slack message is: " + repr(slack_msg))

    event = slack_msg['event']

    # No idea what it means when type is not present.
    if 'type' not in event: return
    t = event['type']

    if t == 'message' and 'subtype' not in event:
        words = event['text'].lower().split()
        if 'hmbot' in words:
            logger.info("I would say hello here")
