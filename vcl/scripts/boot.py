"""
Boot virtual machines
"""

from __future__ import absolute_import

from vcl.spec2 import Cluster
from vcl import openstack
from vcl.state import State


__PROVIDERS = dict(
    openstack = openstack,
    # libvirt = libvirt
)


def add_parser(p):

    from .defaults import \
          spec_filename \
        , inventory_filename \
        , machines_filename

    p.add_argument('--provider', '-p', metavar='STR', default='openstack',
                   help='The VM provider')
    p.add_argument('--cloud', '-c', metavar='STR', default=None,
                   help='The name of the cloud in the specification')
    p.add_argument('--specfile', '-s', metavar='FILE',
                   default=spec_filename, help='The cluster specification file')
    p.add_argument('--inventory', '-i', metavar='FILE',
                   default=inventory_filename,
                   help='The inventory file to write')
    p.add_argument('--dry-run', '-n', default=False, action='store_true',
                   help='Don\'t actually do anything')
    p.add_argument('--machines', '-m', metavar='FILE', default=machines_filename,
                   help='The machine file to write')
    p.add_argument('--prefix', '-P', metavar='STR', default=None, type=str,
                   help='Prefix the name (not hostname) with this string')
    p.add_argument('--timeout-until-active-seconds', '-a', default=None, type=int,
                   help='Number of seconds to wait for a node to become ACTIVE before giving up')
    p.add_argument('--poll-until-active-seconds', '-A', default=None, type=int,
                   help='Number of seconds to wait between polling a new instance to see if it is ACTIVE')


def main(opts):
    global __PROVIDERS

    cluster = Cluster.load_yaml(opts.specfile)
    cluster.assign_to_cloud(opts.cloud)

    if opts.prefix:
        cluster.cloud.parameters.prefix = opts.prefix

    if opts.poll_until_active_seconds:
        cluster.cloud.parameters.poll_until_active_seconds = opts.poll_until_active_seconds

    if opts.timeout_until_active_seconds:
        cluster.cloud.parameters.timeout_until_active_seconds = opts.timeout_until_active_seconds

    state = State(path=opts.machines)
    openstack.boot(cluster, state, dry_run=opts.dry_run)



if __name__ == '__main__':
    opts = getopts()

    main(opts)
    
