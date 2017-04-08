import requests
from html2text import html2text

meetup_events = "https://api.meetup.com/{org}/events?&sign=true&photo-host=public&page={limit}"

def _make_event_attachment(event):
    try:
        time = str(event['time'])[:10]
    except:
        time = ""
    try:
        desc = html2text(event['description'])
    except:
        desc = event.get('description', 'No description.')
    fee = event.get('fee', {}).get('fee', '*FREE*')
    fields = [{
        "title" : "When",
        "value" : f"<!date^{time}^{{date_short}} @ {{time}}|unparsable>",
        "short" : True
    },
    {
        "title" : "Where",
        "value" : f"{event['venue']['name']}",
        "short" : True
    },
    {
        "title" : "Fee",
        "value" : fee,
        "short" : True
    },
    {
        "title" : "RSVP Yes",
        "value" : f"{event['yes_rsvp_count']}",
        "short" : True
    }]
    attachment = {
        "fallback" : event['name'],
        "pretext": f"*<{event['link']}|{event['name']}>*",
        "text" : desc,
        "fields" : fields,
        "mrkdwn_in": ["pretext", "text", "fields"]
    }
    return attachment

def events(org, limit):
    url = meetup_events.format(org=org, limit=limit)
    rsp = requests.get(url)
    if rsp.status_code != requests.codes.ok:
        return False, rsp.status_code

    events = rsp.json()
    attachments = [_make_event_attachment(event) for event in events]
    return True, attachments

