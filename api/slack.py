import logging, json
import requests

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('api')
logger.setLevel(logging.DEBUG)

token = None

def call(method, **kwargs):
    """
    Perform a Slack Web API call. It is supposed to have roughly the same
    semantics as the official slackclient Python library.

    This does some magic "fixups" of the outbound data.
    """
    kwargs['token'] = token
    if 'attachments' in kwargs:
        # I do not fully understand why this is necessary.
        # but attachments do not show up unless we do this.
        kwargs['attachments'] = json.dumps(kwargs['attachments'])
    r = requests.post("https://slack.com/api/" + method, data=kwargs)
    r.raise_for_status()
    response = r.json()
    if not response.get('ok'):
        logger.error(f"Slack error: {response.get('error')}")
        raise Exception(f"Slack error: {response.get('error')}")

    if response.get('warning'):
        logger.warning(f"Slack warning: {response.get('warning')}")

    return response

def respond(msg, text, **kwargs):
    """
    Respond to a message by posting to the channel the request originates from.
    """
    if 'text' in kwargs:
        logger.warn(f'"text" given as kwarg: {kwargs["text"]}')
    if 'channel' in kwargs:
        logger.warn(f'"channel" given as kwarg: {kwargs["channel"]}')
    kwargs['text'] = text
    kwargs['channel'] = msg['channel']
    return call('chat.postMessage', **kwargs)

