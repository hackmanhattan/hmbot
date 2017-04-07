import logging
from contextlib import contextmanager
import spacy

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('hmbot.parser')
logger.setLevel(logging.DEBUG)

nlp = spacy.load('en')

class BackTrack(Exception):
    pass

class NotHandled(Exception):
    pass

class Parser:
    def __init__(self, ignore=None):
        self.ignore = tuple(str(e).lower() for e in ignore) or ()
        self.handlers = []

    def action(self, *args):
        args = tuple(match(arg) if type(arg) == str else arg for arg in args)
        def dec(func):
            self.handlers.append(make_handler(args, func, self.ignore))
        return dec

    def parse(self, text, *args):
        tokens = [str(token).lower() for token in nlp(text)]
        for handler in self.handlers:
            okay, value = handler(tokens, *args)
            if okay:
                return value
        raise NotHandled()

class Stream:
    def __init__(self, tokens, ignore):
        self.offset = 0
        self.tokens = tokens
        self.ignore = ignore

    def abort(self):
        raise BackTrack()

    def rest(self):
        return self.tokens[self.offset:]

    def __next__(self):
        while self.offset < len(self.tokens):
            token = self.tokens[self.offset]
            self.offset += 1
            if token in self.ignore:
                continue
            return token
        raise StopIteration()

    def __str__(self):
        return f"Stream(offset={self.offset}, tokens={self.tokens}, ignore={self.ignore})"

def make_handler(rules, func, ignore):
    def handler(tokens, *args):
        stream = Stream(tokens, ignore)
        for rule in rules:
            ret = rule(stream)
            if not ret:
                return False, None
        return True, func(stream.rest(), *args)
    return handler

@contextmanager
def branch(stream):
    offset = stream.offset
    try:
        yield stream
    except BackTrack:
        stream.offset = offset

def match(string):
    """
    Implements `Adapter` pattern for strings to actions.

    This is used internally to allow code to act uniformly on inputs.
    You don't need to use this from the hmbot library.
    """
    rule = [str(token).lower() for token in nlp(string)]
    def action(stream):
        for part in rule:
            token = next(stream)
            logger.debug(f'match {token} {part}')
            if token != part:
                return False
        return True
    return action

def oneof(*options):
    options = tuple(match(opt) if type(opt) == str else opt for opt in options)
    def action(stream):
        for opt in options:
            with branch(stream):
                if opt(stream):
                    return True
                stream.abort()
        return False
    return action

def maybe(rule):
    if type(rule) == str:
        rule = match(rule)

    def action(stream):
        with branch(stream):
            if not rule(stream):
                stream.abort()
        return True
    return action

