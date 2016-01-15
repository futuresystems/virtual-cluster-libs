
defaults = {
    'libvirt': {
        'cpus' : 1,
        'memory': 1024
    },

    'openstack': {
        'futuresystems': {
            'flavor': 'm1.large',
            'image': 'ubuntu-14.04',
            'key-name': 'gambit',
            'network': 'fgXYZ-net',
            'floating_ip_pool': 'ext-net',
            'security_groups': ['default'],
        },
    },

    'vagrant': {
        'provider': 'libvirt',
        'box': 'ubuntu/14.04'
    }
}
                  

zk = lambda i: {
    'zk%d' % i: {
        'ip': '10.0.0.{}'.format(i+10),
    }
}

master = lambda i: {
    'master%d' % i: {
        'ip': '10.0.1.{}'.format(i+10),
        'openstack.futuresystems': {'security_groups': ['default', 'hadoop-status']}
    }
}

slave = lambda i: {
    'slave%d' % i: {
        'ip': '10.0.2.{}'.format(i+10),
    }
}

frontend = lambda i: {
    'frontend%d' % i: {
        'ip': '10.0.3.{}'.format(i+10),
        'extra_disks': {'device': 'vdb',
                        'size': '10G',}
    }
}

loadbalancer = lambda i: {
    'loadbalancer%d' % i: {
        'ip': '10.0.4.{}'.format(i+10),
        'openstack.futuresystems': {'flavor': 'm1.medium',
                          'security_groups': ['default', 'sshlb'],}

    }
}

monitor = lambda i: {
    'monitor%d' % i: {
        'ip': '10.0.5.{}'.format(i+10),
    }
}

gluster = lambda i: {
    'gluster%d' % i: {
        'ip': '10.0.6.{}'.format(i+10),
        'openstack.futuresystems': {'flavor': 'm1.large',}

    }
}

def expand(fn, count):
    def _work():
        for i in xrange(count):
            yield fn(i)
    return list(_work())

from itertools import chain

machines = list(chain(
    expand(zk, 3),
    expand(master, 3),
    expand(slave, 12),
    expand(frontend, 3),
    expand(loadbalancer, 3),
    expand(monitor, 1),
    expand(gluster, 6)
))




group0 = lambda name, getters: \
        {name:
         list(chain(*list(chain(*[
            map(dict.keys, expand(fn, count)) for fn, count in getters
        ]))))}

def group(name, groupdef):

    def names():
        for fn, indices in groupdef:
            for i in indices:
                yield fn(i).keys()

    return {name: list(chain(*names()))}


def combine(name, *groups):

    def work():
        for group in groups:
            print 'group =', group.keys()
            for names in group.itervalues():
                print 'names =', names
                for n in names:
                    print 'n =', n
                    yield n

    return {name: list(sorted(set(work())))}


zookeepers = group('zookeepers', [(zk, xrange(3))])
namenodes = group('namenodes', [(master, [1,2])])
journalnodes = group('journalnodes', [(master, xrange(3))])
historyservers = group('historyservers', [(master, [3])])
resourcemanagers = group('resourcemanagers', [(master, xrange(3))])
datanodes = group('datanodes', [(slave, xrange(12))])
frontends = group('frontends', [(frontend, xrange(3))])
glusternodes = group('glusternodes', [(gluster, xrange(6))])
hadoopnodes = combine('hadoopnodes', namenodes, datanodes, journalnodes, historyservers)

inventory = [
    zookeepers,
    namenodes,
    journalnodes,
    historyservers,
    resourcemanagers,
    datanodes,
    frontends,
    glusternodes,
    hadoopnodes,
]

spec = {
    'defaults': defaults,
    'machines': machines,
    'inventory': inventory,
}

import yaml
print yaml.dump(spec, default_flow_style=False)
