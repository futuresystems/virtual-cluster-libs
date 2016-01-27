

from vcl.specification import update_spec, mk_nodes, load_spec, inventory_format
from vcl import openstack
import yaml
# from vcl.boot import libvirt

import argparse as A


__PROVIDERS = dict(
    openstack = openstack,
    # libvirt = libvirt
)


def getopts():

    from defaults import \
          spec_filename \
        , inventory_filename \
        , machines_filename

    p = A.ArgumentParser(description='Startup virtual machines')
    p.add_argument('--provider', '-p', metavar='STR', default=None)
    p.add_argument('--specfile', '-s', metavar='FILE', default=spec_filename)
    p.add_argument('--inventory', '-i', metavar='FILE', default=inventory_filename)
    p.add_argument('--dry-run', '-n', default=False, action='store_true')
    p.add_argument('--machines', '-m', metavar='FILE', default=machines_filename)

    return p.parse_args()


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
    
