import requests

math_uri = "http://mathurl.com/render.cgi"

def format(tex):
    p = bytes(''.join(tex), encoding="utf8")
    rsp = requests.get(math_uri, params=p)
    if rsp.status_code != requests.codes.ok:
        return False, rsp.status_code
    return True, rsp.url

