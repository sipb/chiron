#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import urllib
from lxml import etree
import time
import datetime
import sys
from random import choice
import os
import json

try:
    import zephyr
except ImportError:
    import site
    site.addsitedir('/mit/broder/lib/python%s/site-packages' % sys.version[:3])
    import zephyr


seen_timeout = 5 * 60
default_realm = 'ATHENA.MIT.EDU'
parser = etree.HTMLParser(encoding='UTF-8')

def zbody(zgram):
    return zgram.fields[1] if len(zgram.fields) > 1 else zgram.fields[0]

def build_matcher(regex, flags=0):
    r = re.compile(regex, flags)
    def match(zgram):
        return r.findall(zbody(zgram))
    return match

def instance_matcher(regex, flags=0):
    r = re.compile(regex, flags)
    def match(zgram):
        if zgram.opcode.lower() == 'auto':
            return []
        return r.findall(zgram.instance)
    return match

def is_personal(zgram):
    return bool(zgram.recipient)


#####################
# Code for Fetchers #
#####################

# Generic fetchers (parametrizable by site)

def fetch_bugzilla(url):
    def bugzilla_fetcher(ticket):
        u = '%s/show_bug.cgi?id=%s' % (url, ticket)
        f = urllib.urlopen(u)
        t = etree.parse(f, parser)
        title = t.xpath('string(//span[@id="short_desc_nonedit_display"])')
        if title:
            return u, title
        else:
            return u, None
    return bugzilla_fetcher

def fetch_trac(url):
    def trac_fetcher(ticket):
        u = '%s/ticket/%s' % (url, ticket)
        f = urllib.urlopen(u)
        t = etree.parse(f, parser)
        title = t.xpath('string(//h2[@class])')
        if title:
            return u, title
        else:
            return u, None
    return trac_fetcher

def fetch_github(user, repo, ):
    def fetch(ticket):
        u = 'https://api.github.com/repos/%s/%s/issues/%s' % (user, repo, ticket, )
        f = urllib.urlopen(u)
        j = json.load(f)
        try:
            return j['html_url'], j['title']
        except KeyError:
            return u, None
    return fetch

# Project-specific fetchers

fetch_cve_rhbz = fetch_bugzilla("https://bugzilla.redhat.com")
def fetch_cve(ticket):
    # Try fetching from RHBZ first, since it tends to be better
    url, title = fetch_cve_rhbz(ticket)
    print "RHBZ url='%s' title='%s'" % (url, title)
    if title:
        return url, "[RHBZ] " + title

    u = 'http://cve.mitre.org/cgi-bin/cvename.cgi?name=%s' % ticket
    f = urllib.urlopen(u)
    t = etree.parse(f, parser)
    title = t.xpath('string(//tr[th="Description"]/following::tr[1])')
    if title:
        return u, "\n" + title.strip() + "\n"
    else:
        return u, None

def fetch_scripts_faq(ticket):
    u = 'http://scripts.mit.edu/faq/%s' % ticket
    f = urllib.urlopen(u)
    t = etree.parse(f, parser)
    title = t.xpath('string(//h3[@class="storytitle"])')
    if title:
        return u, title
    else:
        return u, None

def fetch_launchpad(ticket):
    u = 'http://api.launchpad.net/1.0/bugs/%s' % ticket
    f = urllib.urlopen(u)
    j = json.load(f)
    try:
        return j['web_link'], j['title']
    except KeyError:
        return u, None

def fetch_debbugs(url):
    def debbugs_fetcher(ticket):
        u = '%s/cgi-bin/bugreport.cgi?bug=%s' % (url, ticket)
        f = urllib.urlopen(u)
        t = etree.parse(f, parser)
        title = t.xpath('normalize-space(//h1/child::text()[2])')
        if title:
            return u, title
        else:
            return u, None
    return debbugs_fetcher

def fetch_pokemon(ticket):
    u = 'http://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_by_National_Pok%C3%A9dex_number'
    f = urllib.urlopen(u + '?action=raw')
    for line in f:
        if line[0:7] == '{{rdex|':
            (id, name) = line.split('|')[2:4]
            try:
                if int(id) == int(ticket):
                    return u, "%s (%s)" % (name, ", ".join(line.split('}')[0].split('|')[5:]))
            except ValueError:
                pass
    return u, None

def fetch_mit_class(ticket):
    u = 'http://student.mit.edu/catalog/search.cgi?search=%s' % (ticket, )
    f = urllib.urlopen(u)
    t = etree.parse(f, parser)
    title = t.xpath('string(//h3)')
    if title:
        return u, title
    else:
        return u, None

def undebathena_fun():
    u = 'http://debathena.mit.edu/trac/wiki/PackageNamesWeDidntUse'
    f = urllib.urlopen(u)
    t = etree.parse(f, parser)
    package = choice(t.xpath('id("content")//li')).text.strip()
    dir = choice(['/etc', '/bin', '/usr/bin', '/sbin', '/usr/sbin',
                  '/dev/mapper', '/etc/default', '/var/run'])
    file = choice(os.listdir(dir))
    return u, "%s should divert %s/%s" % (package, dir, file)

# Special constant-text fetchers

def deal_with_assassin(ticket):
    return ("NO COMBOS OVER ZEPHYR",
"""DO @b(NOT) ASK FOR OR SEND THE OFFICE COMBO
OVER ZEPHYR, EVEN PERSONAL ZEPHYR.
Instead, look in /mit/assassin/Office. If you don't have access,
ask to be added.""")

def invoke_science(ticket):
    return ("SCIENCE!",
"""
  ____   ____ ___ _____ _   _  ____ _____
 / ___| / ___|_ _| ____| \ | |/ ___| ____|
 \___ \| |    | ||  _| |  \| | |   |  _|
  ___) | |___ | || |___| |\  | |___| |___
 |____/ \____|___|_____|_| \_|\____|_____|
""")

def invoke_debothena(ticket):
    return (ticket,
u"""
╺┳┓┏━╸┏┓ ┏━┓╺┳╸╻ ╻┏━╸┏┓╻┏━┓
 ┃┃┣╸ ┣┻┓┃ ┃ ┃ ┣━┫┣╸ ┃┗┫┣━┫
╺┻┛┗━╸┗━┛┗━┛ ╹ ╹ ╹┗━╸╹ ╹╹ ╹
""")


#########################################
# Declarations of MATCHERS and FETCHERS #
#########################################

class MatchEngine(object):
    def __init__(self, ):
        self.matchers = []
        self.fetchers = {}

    def add_fetchers(self, fetchers):
        for name, fetcher in fetchers.items():
            assert name not in self.fetchers
            self.fetchers[name] = fetcher

    def add_matchers(self, matchers):
        for matcher in matchers:
            assert matcher[0] in self.fetchers
        self.matchers.extend(matchers)

    def add_trac(self, name, url, classes=None):
        lname = name.lower()
        if classes is None:
            classes = [lname]
        assert name not in self.fetchers
        self.fetchers[name] = fetch_trac(url)
        trac_matchers = [
            (name, [build_matcher(r'\b%s[-\s:]*#([0-9]{1,5})\b' % (lname, ), re.I)], lambda m: True),
        ]
        for cls in classes:
            trac_matchers.extend([
                (name, [build_matcher(r'\btrac[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m, cls=cls: cls in m.cls),
                # The "-Ubuntu" bit ignores any "uname -a" snippets that might get zephyred
                (name, [build_matcher(r'#([0-9]{2,5})\b(?!-Ubuntu)')], lambda m, cls=cls: cls in m.cls),
            ])
        self.matchers.extend(trac_matchers)

    def find_ticket_info(self, zgram):
        for tracker, ms, cond in self.matchers:
            if cond(zgram):
                for m in ms:
                    ticket = m(zgram)
                    for t in ticket:
                        yield tracker, self.fetchers[tracker], t

match_engine = MatchEngine()

match_engine.add_fetchers({
    'CVE': fetch_cve,
    'Launchpad': fetch_launchpad,
    'Debian': fetch_debbugs('http://bugs.debian.org'),
    'Debothena': fetch_github('sipb', 'debothena'),
    'RHBZ': fetch_bugzilla('https://bugzilla.redhat.com'),
    'pag-screen': fetch_github('sipb', 'pag-screen'),
    'Mosh': fetch_github('keithw', 'mosh'),
    'Scripts FAQ': fetch_scripts_faq,
    'ESP': fetch_github('learning-unlimited', 'ESP-Website'),
    'Pokedex': fetch_pokemon,
    'MIT Class': fetch_mit_class,
    'Assassin': deal_with_assassin,
    'SCIENCE': invoke_science,
    'Debothena Test': invoke_debothena,
    })

match_engine.add_matchers((
    ('CVE', [build_matcher(r'\b(CVE-[0-9]{4}-[0-9]{4})\b', re.I)], lambda m: True),
    ('Launchpad', [build_matcher(r'\blp[-\s:]*#([0-9]{4,8})\b', re.I)], lambda m: True),
    ('Debian', [build_matcher(r'\bdebian[-\s:]#([0-9]{4,6})\b', re.I)], lambda m: True),
    ('Debothena', [build_matcher(r'\bdebothena[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: True),
    ('RHBZ', [build_matcher(r'\bRHBZ[-\s:]#([0-9]{4,7})\b', re.I)], lambda m: True),
    ('pag-screen', [build_matcher(r'\bpag-screen[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: True),
    ('Mosh', [build_matcher(r'\bmosh[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: True),
    ('Scripts FAQ', [build_matcher(r'\bscripts faq[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: True),
    ('Scripts FAQ', [build_matcher(r'\bfaq[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: 'scripts' in m.cls),
    ('ESP', [build_matcher(r'#([0-9]{2,5})\b(?!-Ubuntu)', re.I)], lambda m: 'esp' in m.cls),
    ('ESP', [build_matcher(r'\besp[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: True),
    ('Pokedex', [build_matcher(r'\bpokemon[-\s:]*#([0-9]{1,3})\b', re.I)], lambda m: True),
    ('Pokedex', [build_matcher(r'#([0-9]{1,3})\b', re.I)], lambda m: 'lizdenys' in m.cls),
    ('MIT Class', [build_matcher(r'class ([0-9a-z]{1,3}[.][0-9a-z]{1,4})\b', re.I)], lambda m: True),
    ('MIT Class', [build_matcher(r"what's ([0-9a-z]{1,3}[.][0-9a-z]{1,4})\?\b", re.I)], lambda m: True),
    ('MIT Class', [build_matcher(r'([0-9a-z]{1,3}[.][0-9]{1,4})\b', re.I)], is_personal),
    ('Assassin', [build_matcher(r'\bcombo\b', re.I)], lambda m: 'assassin' in m.cls),
    ('Assassin', [build_matcher(r'\bcombination\b', re.I)], lambda m: 'assassin' in m.cls),
    ('SCIENCE', [build_matcher(r'^science$', re.I)], lambda m: 'axs' in m.cls),
    ('Debothena Test', [build_matcher(r'\bdebothena test[-\s:]*#([0-9]{1,5})\b', re.I)], lambda m: True),
    ))

match_engine.add_trac('Django', 'https://code.djangoproject.com', classes=[])
match_engine.add_trac('Debathena', 'http://debathena.mit.edu/trac', classes=['debathena', 'linerva', 'jdreed', ])
match_engine.add_trac('Scripts', 'http://scripts.mit.edu/trac', )
match_engine.add_trac('XVM', 'http://xvm.scripts.mit.edu/trac', )
match_engine.add_trac('Barnowl', 'http://barnowl.mit.edu', )
match_engine.add_trac('Zephyr', 'http://zephyr.1ts.org', classes=['zephyr-dev'])
match_engine.add_trac('SIPB', 'http://sipb.mit.edu/trac', )
match_engine.add_trac('Remit', 'http://remit.scripts.mit.edu/trac', )
match_engine.add_trac('ASA', 'http://asa.mit.edu/trac', )


#############
# CORE CODE #
#############

def strip_default_realm(principal):
    if '@' in principal:
        user, domain = principal.split('@')
        if domain == default_realm:
            return user
    return principal

def add_default_realm(principal):
    if '@' in principal:
        return principal
    else:
        return "%s@%s" % (principal, default_realm, )

def zephyr_setup():
    zephyr.init()
    subs = zephyr.Subscriptions()
    for c in [
        'broder-test', 'geofft-test', 'adehnert-test',
        'linerva', 'debathena', 'undebathena',
        'sipb', 'scripts', 'barnowl', 'zephyr-dev', 'xvm',
        'geofft', 'lizdenys', 'jdreed', 'axs', 'adehnert', 'achernya', 'kcr', 'jesus', 'nelhage',
        'assassin',
        'remit', 'asa', 'esp',
    ]:
        subs.add((c, '*', '*'))
    subs.add(('message', '*', '%me%'))

cc_re = re.compile(r"CC:(?P<recips>( [a-z./@]+)+) *$", re.MULTILINE)

def format_tickets(last_seen, zgram, tickets):
    messages = []
    for tracker, fetcher, ticket in tickets:
        print "Found ticket at %s on -c %s: %s, %s" % (datetime.datetime.now(), zgram.cls, tracker, ticket, )
        if (zgram.opcode.lower() != 'auto' and
            last_seen.get((tracker, ticket, zgram.cls), 0) < time.time() - seen_timeout):
            if zgram.cls[:2] == 'un':
                u, t = undebathena_fun()
            else:
                u, t = fetcher(ticket)
            if not t:
                t = 'Unable to identify ticket %s' % ticket
            message = '%s ticket %s: %s' % (tracker, ticket, t)
            messages.append((message, u))
            last_seen[(tracker, ticket, zgram.cls)] = time.time()
    return messages

def send_response(zgram, messages):
    z = zephyr.ZNotice()
    z.cls = zgram.cls
    z.instance = zgram.instance
    #z.format = "http://zephyr.1ts.org/wiki/df"
    recipients = set()
    if 'debothena' in zgram.recipient:
        recipients.add(zgram.sender)
        cc = cc_re.match(zbody(zgram))
        if cc:
            cc_recips = cc.group('recips').split(' ')
            for cc_recip in cc_recips:
                if cc_recip and 'debothena' not in cc_recip:
                    recipients.add(add_default_realm(cc_recip.strip()))
        z.sender = zgram.recipient
    else:
        recipients.add(zgram.recipient)
    z.opcode = 'auto'
    if len(messages) > 1:
        body = '\n'.join(["%s (%s)" % (m, url) for m, url in messages])
    else:
        body = '\n'.join([m for m, url in messages])
    if len(recipients) > 1:
        cc_line = " ".join([strip_default_realm(r) for r in recipients])
        body = "CC: %s\n%s" % (cc_line, body)
    z.fields = [url, body]
    print "  -> Reply to: %s" % (recipients, )
    for recipient in recipients:
        z.recipient = recipient
        z.send()

def main():
    last_seen = {}
    zephyr_setup()
    print "Listening..."
    while True:
      try:
        zgram = zephyr.receive(True)
        if not zgram:
            continue
        if zgram.opcode.lower() == 'kill':
            sys.exit(0)
        orig_class = False
        if "-test" in zgram.cls:
            orig_class = zgram.cls
            zgram.cls = zgram.instance
        tickets = match_engine.find_ticket_info(zgram)
        messages = format_tickets(last_seen, zgram, tickets)
        if messages:
            if orig_class:
                zgram.cls = orig_class
            send_response(zgram, messages)
      except UnicodeDecodeError:
        pass

if __name__ == '__main__':
    main()
