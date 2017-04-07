"""
Endpoint for calls made from the Slack Events API.
"""
import json, re, requests, os, sys, logging, bottle
import hmbot

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('endpoint')
logger.setLevel(logging.DEBUG)

slack_token         = os.environ['SLACK_TOKEN']
verification_token  = os.environ['VERIFICATION_TOKEN']

def api_call(method, **kwargs):
    """
    Perform a Slack Web API call. It is supposed to have roughly the same
    semantics as the official slackclient Python library, but
    """
    kwargs['token'] = slack_token
    r = requests.post("https://slack.com/api/" + method, data=kwargs)
    r.raise_for_status()
    response = r.json()
    if not response.get('ok'):
        logger.error(f"Slack error: {response.get('error')}")
        raise Exception(f"Slack error: {response.get('error')}")

    if response.get('warning'):
        logger.warning(f"Slack warning: {response.get('warning')}")

    return response

def handle_post(message):
    if 'type' not in message:
        logger.info(f"type missing in message {message}")
        return

    if message['token'] != verification_token:
        logger.error(f"verification token {message['token']} is wrong")
        return

    t = message['type']

    if t == 'url_verification':
        return message['challenge']
    elif t == 'event_callback':
        return handle_event(message['event'])
    else:
        logger.debug(f"unknown message type {t} in message {message}")

def handle_event(event):
    if 'type' not in event:
        logger.info(f"type missing in event {event}")
        return

    t = event['type']

    if t == 'message':
        return handle_message(event)
    else:
        logger.debug(f"unknown event type {t} in event {event}")

def handle_message(event):
    # Ignore bot messages
    if 'bot_id' in event:
        logger.debug(f"ignoring because this is a bot message")
        return

    if 'subtype' in event:
        logger.debug(f"ignoring because this is a subtyped message")
        return

    logger.debug(f"received event {event}")
    return hmbot.handle_message(event, api_call)

@bottle.post('/')
def slack_event_api():
    # bottle is nice and simply but has a horrible design where request and
    # response are global objects.
    try:
        return handle_post(bottle.request.json) or ''
    except:
        logger.error("Error in handle_event", exc_info=True)
        return ''

# Auto reloading doesn't work that well because it crashes if you have a typo.
if __name__ == '__main__':
    bottle.run(host='0.0.0.0', port=8080)

