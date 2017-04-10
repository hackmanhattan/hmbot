"""
All hmbot functions and state.
"""
import logging, random, requests, subprocess, fcntl, os, pty, time, textwrap
from collections import namedtuple

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

Message = namedtuple("Message", ("command", "state_id", "state", "args", "kwargs"))

def create_process(state, args):
    master, slave = pty.openpty()
    p = subprocess.Popen(args, bufsize=0, stdin=subprocess.PIPE, stdout=slave, close_fds=True)
    stdout = os.fdopen(master)
    state['stdout'] = stdout
    fcntl.fcntl(master, fcntl.F_SETFL, os.O_NONBLOCK)
    state['process'] = p

def pump_process(state, prefix='', postfix='', width=None, wait=True):
    p = state.get('process')
    stdout = state.get('stdout')
    ts = state.get('thread_ts')
    msg = state.get('msg')
    text = [prefix]
    if not msg:
        logger.error("No `msg` in `state`.")
        return
    if not p:
        logger.error("No `process` in `state`.")
        return
    if not stdout:
        logger.error("No `stdout` in `state`.")
        return
    logger.debug(f"Pumping process #{p.pid}.")
    while wait:
        try:
            out = stdout.read(1)
            while out:
                logger.debug(f"Pumped process #{p.pid}: {out}")
                wait = False
                text.append(out)
                out = stdout.read(1)
        except IOError:
            time.sleep(0.1)
    logger.debug(f"Finished pumping process #{p.pid}")
    text.append(postfix)
    text = ''.join(text)
    if width:
        text = ''.join(textwrap.wrap(text, width))
    api.slack.respond(msg, text, thread_ts=ts)

def write_process(state, text):
    """
    Writes `text` to a process.
    """
    p = state.get('process')
    ts = state.get('thread_ts')
    if not p:
        logger.error("No `process` in `state`.")
        return
    text = bytes(text, encoding='utf8')
    logger.debug(f"Writing '{text}' to process #{p.pid}")
    p.stdin.write(text)
    p.stdin.flush()

# We avoid the use of reflection in the message pump by providing this map.
ext_func_table = {
    "create_process" : create_process,
    "write_process" : write_process,
    "pump_process" : pump_process,
}

@parser.action(">")
def game_action(tokens, msg, **kwargs):
    if 'queue' not in kwargs:
        logger.info("Can't find queue.")
        api.slack.respond(msg, "Sorry, I can't play any games right now.  Someone stole my queue.")
        return False

    args = ' '.join(tokens).strip() + '\n'
    queue = kwargs['queue']
    logger.debug(f"Queueing request to write to subprocess: {args}")
    m = Message(
        command="write_process",
        state_id=msg['ts'],
        state={'thread_ts' : msg['ts']},
        args=(args,),
        kwargs={}
    )
    queue.put(m)
    logger.debug("Queueing request to pump subprocess.")
    m = Message(
        command="pump_process",
        state_id=msg['ts'],
        state={},
        args=(),
        kwargs={'width':60}
    )
    queue.put(m)

@parser.action(maybe(oneof(*greetings)), "hmbot", maybe("lets"), "play")
def games(tokens, msg, **kwargs):
    if 'queue' not in kwargs:
        logger.info("Can't find queue.")
        api.slack.respond(msg, "Sorry, I can't play any games right now.  Someone stole my queue.")
        return False

    if not tokens or 'adventure' not in tokens[0]:
        api.slack.respond(msg, "Sorry, I don't know that game :slightly_frowning_face:")
        return False

    queue = kwargs['queue']
    logger.debug("Queueing request to spawn adventure subprocess.")
    m = Message(
        command="create_process",
        state_id=msg['ts'],
        state={'thread_ts' : msg['ts'], 'msg' : msg},
        args=('/usr/bin/adventure',),
        kwargs={}
    )
    queue.put(m)
    logger.debug("Queueing request to pump adventure subprocess.")
    m = Message(
        command="pump_process",
        state_id=msg['ts'],
        state={},
        args=(),
        kwargs={}
    )
    queue.put(m)
    logger.debug(f"Creating thread {msg['ts']}.")
    api.slack.respond(msg, "Okay!  Let's play.  Send me game commands by starting your message with '>'", thread_ts=msg['ts'])

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

