
from socket import gethostname
from itertools import chain
from vcl.specification import expand, group, mk_namespace


defaults = {
    'netmask': '255.255.255.0',
    'public_key': '~/.ssh/id_rsa.pub',
    'domain_name': 'local',
    'extra_disks': {},

    'openstack': {
        'flavor': 'm1.large',
        'image': 'Ubuntu-14.04-64',
        'key_name': gethostname(),
        'network': 'systest-net',
        'assign_floating_ip': False,
        'floating_ip_pool': 'ext-net',
        'security_groups': ['default'],
    },

}

vcl = lambda i: {
    'vcl%d' % i: {
        'ip': '10.0.0.{}'.format(i+10),
    },
}

N_VCL = 2
machines = list(chain(
    expand(vcl, N_VCL)
))


inventory = [
    group('vclnodes', [(vcl, xrange(N_VCL))])
]

spec = dict(
    defaults=defaults,
    machines=machines,
    inventory=inventory,
)

namespace = mk_namespace(spec)


