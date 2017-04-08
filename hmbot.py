"""
All hmbot functions and state.
"""
import logging, random, requests

import api.slack, api.meetup
from parser import oneof, maybe, Parser, NotHandled

from html2text import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')
logger.setLevel(logging.DEBUG)

parser = Parser(ignore=(',', "'"), remove=("'",))

greetings = ('hello', 'hi', 'greetings', 'howdy', '你好', 'goddag', 'hej', 'hejsa', 'hey', 'sup', 'yo')
verbose_request = ('will you please', 'can you please', 'will you', 'can you', 'please')

@parser.action(maybe(oneof(*greetings)), "hmbot", maybe(oneof(*verbose_request)), oneof("choose between", "choose"), maybe(":"))
def choose(tokens, msg):
    choices = [e.strip() for e in ' '.join(tokens).split(',')]
    if choices:
        choice = random.choice(choices)
    else:
        choice = "FAIL!"
    api.slack.respond(msg, choice)

@parser.action(maybe(oneof(*greetings)), "hmbot", "i hate you")
def i_hate_you(tokens, msg):
    api.slack.respond(msg, ":broken_heart:")

@parser.action(maybe(oneof(*greetings)), "hmbot", oneof("i love you", "i am in love with you"))
def i_love_you(tokens, msg):
    api.slack.respond(msg, ":heart:")

@parser.action(maybe(oneof(*greetings)), "hmbot", oneof("whats happening", "what are the haps"), "?")
def what_are_the_haps(text, msg):
    okay, value = api.meetup.events('hackmanhattan', 5)
    if okay:
        api.slack.respond(msg, "Here are some upcoming events:", attachments=value)
    else:
        api.slack.respond(msg, f'Sorry, I dunno.  I get a `{value}` when I try to talk to meetup.')
    return False

@parser.action(maybe(oneof(*greetings)), oneof("I am", "Im"), "hmbot")
def no_im_hmbot(text, msg):
    api.slack.respond(msg, 'Liar!')
    return False

@parser.action(oneof(*greetings), "hmbot")
def hello(text, msg):
    api.slack.respond(msg, 'Hello, I am hmbot!')
    return False

def handle_message(msg):
    logger.debug(f"received message {msg}")

    if 'text' in msg:
        try:
            return parser.parse(msg['text'], msg)
        except NotHandled:
            logger.debug(f"unhandled message {msg}")

