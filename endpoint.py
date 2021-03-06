"""
Endpoint for calls made from the Slack Events API.
"""
import json, re, requests, os, sys, logging, bottle, time, sqlite3, zmq
import hmbot, api.slack, api.meetup

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('endpoint')
logger.setLevel(logging.DEBUG)

db_path            = os.environ['SQLITE_DB']
api.slack.token    = os.environ['SLACK_TOKEN']
verification_token = os.environ['VERIFICATION_TOKEN']

queue = None

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
    return hmbot.handle_message(event, db=conn, queue=queue, api=api)

@bottle.post('/')
@bottle.post('/eb83190ba19fb434e1bc7ed1b0074497df834db1debe093f97b36cd5b3262c31')
def slack_event_api():
    # bottle is nice and simply but has a horrible design where request and
    # response are global objects.
    try:
        return handle_post(bottle.request.json) or ''
    except:
        logger.error("Error in handle_post", exc_info=True)
        return ''

# Auto reloading doesn't work that well because it crashes if you have a typo.
if __name__ == '__main__':
    conn = sqlite3.connect(db_path)
    hmbot.db.setup(conn)

    context = zmq.Context()
    queue = context.socket(zmq.PUSH)
    queue.bind("tcp://127.0.0.1:5557")

    bottle.run(host='0.0.0.0', port=8080)

