import dns
import dns.resolver
import dns.rdatatype

from typing import List


def dns_resolve(domain: str, records: List[str] = ['A', 'AAAA']) -> list:
    addrs = []

    resolver = dns.resolver.Resolver(configure=False)
    # Default to Google DNS
    resolver.nameservers = ['8.8.8.8', '8.8.4.4']

    for rec in records:
        wanted_rdtype = getattr(dns.rdatatype, rec)
        try:
            answers = resolver.resolve(domain, rec).response.answer
            for answer in answers:
                for item in answer:
                    if item.rdtype == wanted_rdtype:
                        addrs.append(item.to_text())
        except dns.resolver.NoAnswer:
            pass
    return addrs
