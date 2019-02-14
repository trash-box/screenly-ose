'''
    Abfrage des DNS Server auf einen MQTT Server

    Beispiel von: https://github.com/Tertiush/ParadoxIP150v2/blob/master/lib/client.py
    mit dnspython http://www.dnspython.org/ bzw. https://github.com/rthalley/dnspython
'''

HAVE_DNS = True
try:
    import dns.resolver
except ImportError:
    HAVE_DNS = False

import socket

def findMqtt(domain=None):
    if domain is None:
        domain = socket.getfqdn()
        domain = domain[domain.find('.') + 1:]

    try:
        rr = '_mqtt._tcp.%s' % domain
        answers = []
        for answer in dns.resolver.query(rr, dns.rdatatype.SRV):
            addr = answer.target.to_text()[:-1]
            answers.append((addr, answer.port, answer.priority, answer.weight))
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        raise ValueError("No answer/NXDOMAIN for SRV in %s" % (domain))

findMqtt()