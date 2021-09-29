import dns
import dns.resolver
import dns.rdatatype


def dns_resolve(domain: str) -> list:
    addrs = []

    resolver = dns.resolver.Resolver(configure=False)
    # Default to Google DNS
    resolver.nameservers = ['8.8.8.8', '8.8.4.4']

    try:
        for answer in resolver.resolve(domain, 'A').response.answer:
            for item in answer:
                if item.rdtype == dns.rdatatype.A:
                    addrs.append(item.address)
    except dns.resolver.NoAnswer:
        pass

    try:
        for answer in resolver.resolve(domain, 'AAAA').response.answer:
            for item in answer:
                if item.rdtype == dns.rdatatype.AAAA:
                    addrs.append(item.address)
    except dns.resolver.NoAnswer:
        pass

    return addrs
