"""
All hmbot functions and state.
"""
import logging, random, requests, subprocess

import ioc, api.slack, api.meetup
from parser import oneof, maybe, Parser, NotHandled

from html2text import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')
logger.setLevel(logging.DEBUG)

db = ioc.DatabaseProvider('hmbot')
parser = Parser(ignore=(',', "'"), remove=("'",))

greetings = ('hello', 'hi', 'greetings', 'howdy', '你好', 'goddag', 'hej', 'hejsa', 'hey', 'sup', 'yo')
verbose_request = ('will you please', 'can you please', 'will you', 'can you', 'please')

@db.table(choose=(("choices", "TEXT"), ("choice", "TEXT")))
@parser.action(maybe(oneof(*greetings)), "hmbot", maybe(oneof(*verbose_request)), oneof("rechoose between", "rechoose", "choose between", "choose"), maybe(":"))
def choose(tokens, msg, **kwargs):
    tokens = ' '.join(tokens)
    choices = [e.strip() for e in tokens.split(',')]
    if choices:
        choice = random.choice(choices)
    else:
        choice = "FAIL!"
    try:
        if 'db' in kwargs:
            db = kwargs['db']
            if 'rechoose' in msg['text'][:-(len(tokens) - 1)]:
                logger.debug(f'rechoosing: "{choice}" from "{choices}".')
                db.execute(f"DELETE FROM choose WHERE choices = ?", (tokens,))
                db.execute(f"INSERT INTO choose VALUES (?, ?)", (tokens, choice))
            else:
                logger.debug('fetching choice from database.')
                q = db.execute(f"SELECT choice FROM choose WHERE choices = ?", (tokens,))
                cache = q.fetchone()
                if cache:
                    choice = cache[0]
                else:
                    logger.debug(f'inserting {choice} into database.')
                    db.execute(f"INSERT INTO choose VALUES (?, ?)", (tokens, choice))
            db.commit()
        else:
            logger.info('No db supplied to `choose` action.')
    except:
        logger.exception("Database error.")
    api.slack.respond(msg, choice)
    return False

@parser.action(maybe(oneof(*greetings)), "hmbot", "i hate you")
def i_hate_you(tokens, msg, **kwargs):
    api.slack.respond(msg, ":broken_heart:")

@parser.action(maybe(oneof(*greetings)), "hmbot", oneof("i love you", "i am in love with you"))
def i_love_you(tokens, msg, **kwargs):
    api.slack.respond(msg, ":heart:")

@parser.action(maybe(oneof(*greetings)), "hmbot", oneof("whats happening", "what are the haps"), "?")
def what_are_the_haps(text, msg, **kwargs):
    okay, value = api.meetup.events('hackmanhattan', 5)
    if okay:
        api.slack.respond(msg, "Here are some upcoming events:", attachments=value)
    else:
        api.slack.respond(msg, f'Sorry, I dunno.  I get a `{value}` when I try to talk to meetup.')
    return False

@parser.action(maybe(oneof(*greetings)), oneof("I am", "Im"), "hmbot")
def no_im_hmbot(text, msg, **kwargs):
    api.slack.respond(msg, 'Liar!')
    return False

@parser.action(oneof(*greetings), "hmbot")
def hello(text, msg, **kwargs):
    api.slack.respond(msg, 'Hello, I am hmbot!')
    return False

def handle_message(msg, **kwargs):
    logger.debug(f"received message {msg}")

    if 'text' in msg:
        try:
            return parser.parse(msg['text'], msg, **kwargs)
        except NotHandled:
            logger.debug(f"unhandled message {msg}")

