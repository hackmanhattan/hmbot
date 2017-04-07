"""
All hmbot functions and state.
"""
import logging, random, requests, json
from parser import oneof, maybe, Parser, NotHandled
from html2text import html2text

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot')
logger.setLevel(logging.DEBUG)

parser = Parser(ignore=(',', "'"), remove=("'",))

meetup_events = "https://api.meetup.com/hackmanhattan/events?&sign=true&photo-host=public&page=5"

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

@parser.action(maybe(oneof(*greetings)), "hmbot", oneof("i love you", "i am in love with you"))
def i_love_you(tokens, msg, api_call):
    api_call('chat.postMessage', channel=msg['channel'], text=":heart:")

@parser.action(maybe(oneof(*greetings)), "hmbot", oneof("whats happening", "what are the haps"))
def what_are_the_haps(text, msg, api_call):
    rsp = requests.get(meetup_events)
    if rsp.status_code != requests.codes.ok:
        api_call('chat.postMessage', channel=msg['channel'], text='Sorry, I dunno.  I get a {rsp.status_code} when I try to talk to meetup.')
        return False
    events = rsp.json()
    attachments = []
    for event in events:
        try:
            time = str(event['time'])[:10]
            desc = html2text(event['description'])
            attachments.append({
                "fallback" : event['name'],
                "title" : event['name'],
                "title_link" : event['link'],
                "text" : desc,
                "fields" : [
                    {
                        "title" : "When",
                        "value" : f"<!date^{time}^{{date_short}}|unparsable>",
                        "short" : True
                    },
                    {
                        "title" : "Where",
                        "value" : f"{event['venue']['name']}",
                        "short" : True
                    }
                ],
                "mrkdwn_in": ["text"]
            })
        except:
            pass
    api_call('chat.postMessage', channel=msg['channel'], text="Here are some upcoming events:", attachments=json.dumps(attachments))
    return False

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

