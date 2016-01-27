
from socket import gethostname
from itertools import chain
import os
from vcl.specification import expand, group, mk_namespace


defaults = {
    'netmask': '255.255.255.0',
    'public_key': '~/.ssh/id_rsa.pub',
    'private_key':'~/.ssh/id_rsa',
    'domain_name': 'local',
    'extra_disks': {},

    'openstack': {
        'flavor': 'm1.large',
        'image': 'Ubuntu-14.04-64',
        'key_name': gethostname(),
        'network': '{}-net'.format(os.getenv('OS_PROJECT_NAME')),
        'create_floating_ip': True,
        'floating_ip_pool': 'ext-net',
        'security_groups': ['default'],
    },

    'provider': 'openstack',

}

vcl = lambda i: {
    'vcl%d' % i: {
        'ip': '10.0.0.{}'.format(i+10),
    },
}

N_VCL = 1
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


