import json, re, requests, os, sys, logging, bottle

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')

slack_token = os.environ['SLACK_TOKEN']

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
        
@bottle.post('/')
def slack_event_api():
    # bottle is nice and simply but has a horrible design where request and
    # response are global objects.
    logger.debug("Received JSON object " + bottle.request.json)
    return ''

# Auto reloading doesn't work that well because it crashes if you have a typo.
bottle.run(host='0.0.0.0', port=os.environ.get('PORT', 8080), reload=True)
