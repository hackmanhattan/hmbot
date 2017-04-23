"""
All hmbot functions and state.
"""
import logging, random, requests, subprocess, fcntl, os, pty, time

import database
from parser import oneof, maybe, Parser, NotHandled

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')
logger.setLevel(logging.DEBUG)

db = database.DatabaseProvider('hmbot')
parser = Parser(ignore=(',', "'"), remove=("'",))

greetings = oneof('hello', 'hi', 'greetings', 'howdy', '你好', 'goddag', 'hej', 'hejsa', 'hey', 'sup', 'yo')
verbose_request = oneof('will you please', 'can you please', 'will you', 'can you', 'please')

class Help:
    fun = "#5cb85c"
    util = "#5bc0de"
    admin = "#d9534f"

    def __init__(self):
        self.commands = []

    def usage(self, name, doc=None, command_type="#999999"):
        def dec(func):
            self.commands.append((name, doc or (func.__doc__ or "").split("\n")[0], command_type))
            return func
        return dec

helper = Help()

@helper.usage("hmbot, help!", command_type=Help.util)
@parser.action(maybe(greetings), "hmbot", maybe(verbose_request), oneof("help me", "help", "--help"))
def help_me(tokens, msg, api=None, **kwargs):
    """Displays this very message."""

    attachments = []
    for (name, doc, color) in helper.commands:
        attachments.append({
            "title": name,
            "text": doc,
            "color" : color,
            "mrkdwn_in": ["text", "pretext", "title"]
        })
    api.slack.respond(msg, "Okay, here are some of the things I can do:", attachments=attachments, thread_ts=msg.get('thread_ts'))

@parser.action(">")
@parser.action("&", "gt", ";")
def process_write(tokens, msg, queue=None, **kwargs):
    """Request that the text of this message be sent to the process associated with this thread."""

    args = ' '.join(tokens).strip() + '\n'
    queue.send_json({
        'slack_msg' : msg,
        'thread_id' : msg['thread_ts'],
        'command' : 'write',
        'input' : args
    })

@helper.usage("# ps", command_type=Help.admin)
@parser.action("# ps")
def ps(tokens, msg, queue=None, api=None, **kwargs):
    """List all active processes"""

    logger.debug("Queueing request.")
    queue.send_json({
        'slack_msg' : msg,
        'thread_id' : msg.get('thread_ts'),
        'command' : 'ps'
    })

@helper.usage("# kill <pid>", command_type=Help.admin)
@parser.action("# kill")
def kill(tokens, msg, queue=None, api=None, **kwargs):
    """Kill a process."""

    if len(tokens) != 1:
        api.slack.respond(msg, "Usage: # kill <pid>", thread_ts=msg.get('thread_ts'))
        return

    logger.debug("Queueing request.")
    queue.send_json({
        'slack_msg' : msg,
        'thread_id' : msg.get('thread_ts'),
        'command' : 'kill',
        'pid' : int(tokens[0])
    })

@helper.usage("Yo hmbot, let's play <game>!", command_type=Help.fun)
@parser.action(maybe(greetings), "hmbot", maybe("lets"), "play")
def games(tokens, msg, queue=None, api=None, **kwargs):
    """Start playing a game.  Right now the only game I know is 'Adventure'."""

    if not tokens or 'adventure' not in tokens[0]:
        api.slack.respond(msg, "Sorry, I don't know that game :slightly_frowning_face:")
        return False

    logger.debug("Queueing request to spawn adventure subprocess.")
    queue.send_json({
        'slack_msg' : msg,
        'thread_id' : msg['ts'],
        'command' : 'create',
        'width' : 55,
        'input' : '/usr/games/adventure'
    })
    api.slack.respond(msg, "Okay!  Let's play.  Send me game commands by starting your message with '>'", thread_ts=msg['ts'])

@db.table(choose=(("choices", "TEXT"), ("choice", "TEXT")))
@helper.usage("Yo hmbot, (re)choose: <a>, <b>, ...", command_type=Help.fun)
@parser.action(maybe(greetings), "hmbot", maybe(verbose_request), oneof("rechoose between", "rechoose from", "rechoose", "choose between", "choose from", "choose"), maybe(":"))
def choose(tokens, msg, db=None, api=None, **kwargs):
    """Choose an item from a list.  Often with a comedic results.  I will remember my choices, but you can always ask me to rechoose :wink:"""

    tokens = ' '.join(tokens)
    choices = [e.strip() for e in tokens.split(',')]
    if len(choices) == 1:
        if ' or ' in choices[0]:
            choices = [e.strip() for e in choices.split('or')]
        elif ' and ' in choices[0]:
            choices = [e.strip() for e in choices.split('or')]
    if choices:
        choice = random.choice(choices)
    else:
        choice = "FAIL!"
    try:
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
    except:
        logger.exception("Database error.")
    api.slack.respond(msg, choice)

@parser.action(maybe(greetings), "hmbot", "i hate you")
def i_hate_you(tokens, msg, api=None, **kwargs):
    api.slack.respond(msg, ":broken_heart:")

@helper.usage("Yo hmbot, I love you.", command_type=Help.fun) 
@parser.action(maybe(greetings), "hmbot", oneof("i love you", "i am in love with you"))
def i_love_you(tokens, msg, api=None, **kwargs):
    """Feel free to express your undying love for Hmbot."""
    api.slack.respond(msg, ":heart:")

@helper.usage("Yo hmbot, what are the happs?", command_type=Help.util)
@parser.action(maybe(greetings), "hmbot", oneof("whats happening", "what are the haps"), "?")
def what_are_the_haps(text, msg, api=None, **kwargs):
    """Get a list of upcoming events from the hackmanhattan meetup."""

    okay, value = api.meetup.events('hackmanhattan', 5)
    if okay:
        api.slack.respond(msg, "Here are some upcoming events:", attachments=value)
    else:
        api.slack.respond(msg, f'Sorry, I dunno.  I get a `{value}` when I try to talk to meetup.')

@parser.action(maybe(greetings), oneof("I am", "Im"), "hmbot")
def no_im_hmbot(text, msg, api=None, **kwargs):
    api.slack.respond(msg, 'Liar!')

@parser.action(greetings, "hmbot")
def hello(text, msg, api=None, **kwargs):
    api.slack.respond(msg, 'Hello, I am hmbot!')

def handle_message(msg, **kwargs):
    logger.debug(f"Received message {msg}.")

    if 'text' in msg:
        try:
            return parser.parse(msg['text'], msg, **kwargs)
        except NotHandled as ex:
            logger.debug(f"unhandled message '{msg}', with tokens '{ex.tokens}'")
            return
    logger.debug(f"No message text in {msg}.")

