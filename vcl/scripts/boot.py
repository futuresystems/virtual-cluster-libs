

from vcl.specification import mk_namespace, mk_nodes, load_spec
from vcl import openstack
# from vcl.boot import libvirt

import argparse as A


__PROVIDERS = dict(
    openstack = openstack,
    # libvirt = libvirt
)


def getopts():
    p = A.ArgumentParser(description='Startup virtual machines')
    p.add_argument('--provider', '-p', required=True)
    p.add_argument('specfile', metavar='FILE', default='spec.py')
    p.add_argument('--inventory', '-i', default='inventory.yaml')

    return p.parse_args()


def main(provider, nodes, *args, **kws):
    global __PROVIDERS

    module = __PROVIDERS[provider]
    module.boot(nodes, *args, **kws)


if __name__ == '__main__':
    opts = getopts()

    spec = load_spec(opts.specfile)
    nodes = mk_nodes(opts.provider, mk_namespace(spec))

    main(opts.provider, nodes)

    # TODO: write_inventory(opts.inventory, mod.inventory, nodes)
    
