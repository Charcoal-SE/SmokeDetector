import dns
import dns.resolver
import dns.rdatatype

class DNSResolver(dns.resolver.Resolver):

    def __init__(self, filename='/etc/resolv.conf', configure=False,
                 nameservers: Union[str, List[str]] = None):
        # Run the dns.resolver.Resolver superclass init call to configure
        # the object. Then, depending on the value in configure argument,
        # do something with the nameservers argument, which is unique to this
        # class object instead.
        super(DNSResolver, self).__init__(filename, configure)

        if not configure:
            if isinstance(nameservers, str):
                self.nameservers = [nameservers]
            elif isinstance(nameservers, list):
                self.nameservers = nameservers
            else:
                # Fallback to using Google DNS servers
                self.nameservers = ['8.8.8.8, 8.8.4.4']
                
def dns_resolve(domain: str, resolver: DNSResolver = DNSResolver(configure=True)) -> list:
    addrs = []

    for answer in resolver.query(domain, 'A').response.answer:
        for item in answer:
            addrs.append(item.address)

    for answer in resolver.query(domain, 'AAAA').response.answer:
        for item in answer:
            addrs.append(item.address)

    return addrs
