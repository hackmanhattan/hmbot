"""
All hmbot functions and state.
"""
import logging, random
from parser import oneof, maybe, Parser, NotHandled

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')
logger.setLevel(logging.DEBUG)

parser = Parser(ignore=(','))

greetings = ('hello', 'hi', 'greetings', 'howdy', '你好', 'goddag', 'hej', 'hejsa', 'hey', 'sup')

@parser.action(oneof(*greetings), "hmbot")
def hello(text, msg, api_call):
    api_call('chat.postMessage', channel=msg['channel'], text='Hello, I am hmbot!')
    return False

def handle_message(msg, api_call):
    logger.debug(f"received message {msg}")

    if 'text' in msg:
        try:
            return parser.parse(msg['text'], msg, api_call)
        except NotHandled:
            logger.debug(f"unhandled message {msg}")

