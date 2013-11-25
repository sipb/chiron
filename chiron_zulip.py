import chiron
import zulip

class ZulipMessage(chiron.Message):
    def __init__(self, client, zulip):
        self._client = client
        self._zulip = zulip

    def body(self): return self._zulip['content']

    def cls(self): return self._zulip['display_recipient']

    def instance(self): return self._zulip['subject']

    def sender(self): return self._zulip['sender_email']

    def recipient(self): return "(ignored)"

    def is_personal(self):
        return self._zulip['type'] == 'private'

    def send_reply(self, messages):
        zulip = self._zulip
        reply = {}

        if self.is_personal():
            reply['type'] = 'private'
            reply['to'] = [r['email'] for r in zulip['display_recipient']]
        else:
            reply['type'] = 'stream'
            reply['to'] = zulip['display_recipient']
            reply['subject'] = zulip['subject']

        if len(messages) > 0:
            body = '\n'.join(["[%s](%s)" % (m, url) for m, url in messages])
        else:
            body = "No ticket number found in message."
        reply['content'] = body

        if messages or self.is_personal():
            print "  ->", self._client.send_message(reply)

def build_processor(match_engine, client):
    def process(zulip):
        msg = ZulipMessage(client, zulip)
        if '-bot' in msg.sender():
            print "Skipping message from %s:" % (msg.sender(), )
            msg.log_arrival()
        else:
            match_engine.process(msg)
    return process


def main(match_engine):
    client = zulip.Client()
    print "Listening..."
    message_callback = build_processor(match_engine, client)
    client.call_on_each_message(message_callback)