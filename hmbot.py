"""
All hmbot functions and state.
"""
import logging, random, requests
from parser import oneof, maybe, Parser, NotHandled

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')
logger.setLevel(logging.DEBUG)

parser = Parser(ignore=(',', "'"), remove=("'",))

greetings = ('hello', 'hi', 'greetings', 'howdy', '你好', 'goddag', 'hej', 'hejsa', 'hey', 'sup', 'yo')
verbose_request = ('will you please', 'can you please', 'will you', 'can you', 'please')

@parser.action(maybe(oneof(*greetings)), "hmbot", maybe(oneof(*verbose_request)), oneof("choose between", "choose"), maybe(":"))
def choose(tokens, msg, api_call):
    choices = [e.strip() for e in ' '.join(tokens).split(',')]
    if choices:
        choice = random.choice(choices)
    else:
        choice = "FAIL!"
    api_call('chat.postMessage', channel=msg['channel'], text=choice)

@parser.action(maybe(oneof(*greetings)), oneof("I am", "Im"), "hmbot")
def no_im_hmbot(text, msg, api_call):
    api_call('chat.postMessage', channel=msg['channel'], text='Liar!')
    return False

# @parser.action(oneof(*greetings), "hmbot")
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

