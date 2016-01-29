"""
Boot virtual machines
"""

from __future__ import absolute_import

from vcl.specification import update_spec, mk_nodes, load_spec, inventory_format
from vcl import openstack
import yaml
# from vcl.boot import libvirt


__PROVIDERS = dict(
    openstack = openstack,
    # libvirt = libvirt
)


def add_parser(p):

    from .defaults import \
          spec_filename \
        , inventory_filename \
        , machines_filename

    p.add_argument('--provider', '-p', metavar='STR', default=None,
                   help='The VM provider')
    p.add_argument('--specfile', '-s', metavar='FILE',
                   default=spec_filename, help='The cluster specification file')
    p.add_argument('--inventory', '-i', metavar='FILE',
                   default=inventory_filename,
                   help='The inventory file to write')
    p.add_argument('--dry-run', '-n', default=False, action='store_true',
                   help='Don\'t actually do anything')
    p.add_argument('--machines', '-m', metavar='FILE', default=machines_filename,
                   help='The machine file to write')


def main(opts):
    global __PROVIDERS

    spec = load_spec(opts.specfile)
    nodes = mk_nodes(spec, provider=opts.provider)
    update_spec(spec, nodes)

    provider = opts.provider or spec.defaults.provider

    module = __PROVIDERS[provider]
    machines = module.boot(nodes, dry_run=opts.dry_run)

    with open(opts.machines, 'w') as fd: fd.write('')

    for m in machines:
        with open(opts.machines, 'a') as fd:
            o = {m.hostname: m.to_simple_types()}
            s = yaml.dump(o, default_flow_style=False)
            fd.write(s)

    with open(opts.inventory, 'w') as fd:
        i = inventory_format(spec)
        fd.write(i)

    # TODO: write_inventory(opts.inventory, mod.inventory, nodes)



if __name__ == '__main__':
    opts = getopts()

    main(opts)
    
