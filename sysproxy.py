"""
The `System Proxy` or `sysproxy` acts as a bridge between bottle and the host system.

Overview
--------

When a bottle process sends a create message to the `sysproxy` the proxy will attempt to create a new process.
Whenever the process writes to its `stdout` the proxy will send the output to a slack channel or thread specified in the create message.
Whenever a user posts a string starting with '>' to a thread,
hmbot will check to see if any processes are registered with the thread.
If so, hmbot will send a write message to the proxy,
which will cause the proxy to write the string (minus leading '>') to the associated process.

Limitations
-----------

* The proxy never sends messages to a bottle process.
* If you want to send further input to a process, you must create a slack thread that will be associated with the process.
* We don't currently capture the `stderr` of the long lived processes, but we may in the future.
"""

import logging, subprocess, sys, os, pty, time, select, fcntl, textwrap, datetime
import zmq
import api.slack

api.slack.token = os.environ['SLACK_TOKEN']

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('sysproxy')
logger.setLevel(logging.DEBUG)

processes = {}

class WidthHeuristic:
    def __init__(self, width):
        self.width = width

    def apply(self, text):
       return ''.join(textwrap.wrap(text, self.width))

heuristics = {
    'width' : WidthHeuristic
}

class Process:
    def __init__(self, msg, handle, stdout, fid, slv):
        self._fid = fid
        self._slv = slv
        self._msg = msg
        self._handle = handle
        self._stdout = stdout

        heurs = msg.get('heuristics', {}).items()
        self._heuristics = tuple(heuristics[key](value) for (key, value) in heurs)

        self.pid = self._handle.pid
        self.tid = msg['slack_msg']['ts']
        self.created_by = msg['slack_msg']['user']
        self.created_time = datetime.datetime.now()
        self.last_active = self.created_time
        self.command = msg['input']

    def fileno(self):
        return self._fid

    def read(self):
        out = self._stdout.read()
        if 'width' in self._msg:
            width = self._msg['width']
            out = '\n'.join(textwrap.wrap(out, width))
        self._last_active = datetime.datetime.now()
        return out

    def write(self, text):
        text = bytes(msg['input'], encoding='utf8')
        self._handle.stdin.write(text)
        self._handle.stdin.flush()
        self.last_active = datetime.datetime.now()

    def __del__(self):
        logger.debug(f"Destroying process #{self.pid}")
        if not self._handle.poll():
            self._handle.kill()
        os.close(self._fid)
        os.close(self._slv)

def check_for_thread_id(thread_id):
    for p in processes.values():
        if p._msg['thread_id'] == thread_id:
            return p
    return False

def errors_to_attachments(errors):
    attachments = []
    for error in errors:
        attachments.append({
            "fallback" : "An error has occurred.",
            "pretext": "stderr",
            "text" : error,
            "color" : "danger"
        })
    return attachments

def processes_to_attachments(processes):
    attachments = []
    for p in processes:
        attachments.append({
            "fallback" : "process",
            "pretext" : p.command,
            "fields" : [
                {
                    "title" : "Created",
                    "value" : api.slack.datetime_to_slacktime(p.created_time),
                    "short" : True
                },
                {
                    "title" : "Creator",
                    "value" : p.created_by,
                    "short" : True
                },
                {
                    "title" : "Last Active",
                    "value" : api.slack.datetime_to_slacktime(p.last_active),
                    "short" : True
                },
                {
                    "title" : "PID",
                    "value" : p.pid,
                    "short" : True
                }
            ]
        })
    return attachments

def apply_heuristics(text, heuristics):
    for e in heuristics:
        text = e.apply(text)
    return text

def send_errors(msg, text, errors):
    if isinstance(errors, str):
        errors = [errors]
    attachments = errors_to_attachments(errors)
    api.slack.respond(msg, text, attachments=attachments)

def ps(msg):
    attachments = processes_to_attachments(processes.values())
    api.slack.respond(
        msg['slack_msg'], "There are %d active processes." % len(processes),
        attachments=attachments,
        thread_ts=msg['thread_id'])

def kill(msg):
    pid = msg['pid']
    process = processes.get(pid)
    if process:
        del processes[pid]
        api.slack.respond(msg['slack_msg'], ":skull:")
    else:
        api.slack.respond(msg['slack_msg'], "No such process.")

def create_process(msg):
    if 'thread_id' not in msg:
        # No thread id, so we should create a process,
        # wait for it to die, and then respond to the channel with its output.
        create_short_process(msg)
    else:
        create_long_process(msg)

def create_long_process(msg):
    thread_id = msg['thread_id']
    process = check_for_thread_id(thread_id)
    if process:
        error = f"A process is already associated with this thread id: {thread_id} -> {process.pid}."
        logger.error(error)
        attachments = errors_to_attachments([error])
        api.slack.respond(msg['slack_msg'], "No can do amigo!", attachments=attachments, thread_ts=thread_id)
        return
    args = msg['input']
    master, slave = pty.openpty()
    process = subprocess.Popen(args, bufsize=0, stdin=subprocess.PIPE, stdout=slave, close_fds=True)
    fcntl.fcntl(master, fcntl.F_SETFL, os.O_NONBLOCK)
    stdout = os.fdopen(master)

    process = Process(msg, process, stdout, master, slave)
    processes[process.pid] = process

def create_short_process(msg):
    args = msg.get('input')
    if args:
        process = subprocess.Popen(args, bufsize=0, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    else:
        process = subprocess.Popen(args, bufsize=0, stdout=subprocess.PIPE)
    stdout, stderr = process.communicate(bytes(args, encoding='utf8'))
    toapply = tuple(heuristics[key](value) for (key, value) in msg.get('heuristics', {}).items())
    for f in toapply:
        stdout = f(stdout)
        stderr = f(stderr)
    if stderr:
        send_errors(msg['slack_msg'], "Oh no, it looks like something bad happened.", stderr)
    else:
        api.slack.respond(msg['slack_msg'], stdout)

def pump():
    rr, _, _ = select.select(processes.values(), (), (), 1)
    if rr:
        logger.debug("Pumping '%d' pipes...", len(rr))
    for p in rr:
        try:
            out = p.read()
            if out:
                api.slack.respond(msg['slack_msg'], out, thread_ts=p.tid)
        except:
            logger.exception(f"Problem reading from process #{p.pid}.")
    if rr:
        logger.debug("... done pumping.")
        return True
    return False

def write_process(msg):
    """
    Writes `text` to a process.
    """
    text = msg['input']
    process = check_for_thread_id(msg['thread_id'])
    if not process:
        logger.error("No process found for thread.")
        send_errors(
            msg['slack_msg'],
            "Oh no, I forgot what we were doing in this thread.  You should start a new one!",
            f"no process associated with this thread ({msg['thread_id']}).")
        return
    logger.debug(f"Writing '{text}' to process #{process._handle.pid}")
    process.write(text)

if __name__ == '__main__':
    context = zmq.Context()
    consumer_receiver = context.socket(zmq.PULL)
    consumer_receiver.connect("tcp://127.0.0.1:5557")

    commands = {
        'ps' : ps,
        'kill' : kill,
        'quit' : lambda _: sys.exit(0),
        'write' : write_process,
        'create' : create_process,
    }

    while True:
        try:
            msg = consumer_receiver.recv_json(flags=zmq.NOBLOCK)
            logger.info(f"Received message: {msg}.")
            command = commands.get(msg.get('command'))
            if command:
                command(msg)
            else:
                logger.error(f"Unknown message type: {msg['type']}.")
        except zmq.Again:
            if not pump():
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Quiting from keyboard interrupt.")
            break
        except:
            logger.exception("Exception reached top of main loop.")

