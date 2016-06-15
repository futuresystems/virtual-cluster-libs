"""
List running VMs
"""

from __future__ import absolute_import

from vcl.state import State


def add_parser(p):

    from .defaults import machines_filename

    p.add_argument('--state', '-s', metavar='FILE',
                   default=machines_filename,
                   help='Path to the persistent state')



def main(opts):

    state = State(path=opts.state)
    cluster = state.get_cluster()

    for m in cluster.machines:
        print m.name
