

from vcl.specification import update_spec, mk_nodes, load, inventory_format
from vcl import openstack
import yaml
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
    p.add_argument('--dry-run', '-n', default=False, action='store_true')
    p.add_argument('--machines', '-m', default='machines.yml')

    return p.parse_args()


def main(opts):
    global __PROVIDERS

    spec = load(opts.specfile)
    nodes = mk_nodes(opts.provider, spec)
    update_spec(spec, nodes)

    module = __PROVIDERS[opts.provider]
    machines = module.boot(nodes, dry_run=opts.dry_run)

    with open(opts.machines, 'w') as fd: fd.write('')

    for m in machines:
        with open(opts.machines, 'a') as fd:
            o = {m.hostname: m}
            s = yaml.dump(o, default_flow_style=False,
                          canonical=False, default_style='')
            fd.write(s)

    with open(opts.inventory, 'w') as fd:
        i = inventory_format(spec)
        fd.write(i)

    # TODO: write_inventory(opts.inventory, mod.inventory, nodes)



if __name__ == '__main__':
    opts = getopts()

    main(opts)
    
