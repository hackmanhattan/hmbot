import json, re, requests, os, sys, logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')

slack_token = os.environ['SLACK_TOKEN']

def api_call(method, **kwargs):
    kwargs['token'] = slack_token
    r = requests.post("https://slack.com/api/" + method, data=kwargs)
    r.raise_for_status()
    response = r.json()
    if not response.get('ok'):
        raise Exception(f"Slack error: {response.get('error')}")
    return response

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
