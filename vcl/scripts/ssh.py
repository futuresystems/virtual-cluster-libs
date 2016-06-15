"""
Ssh into a machines
"""

from __future__ import absolute_import

from vcl.state import State

from subprocess import call
import sys
from pipes import quote


def add_parser(p):

    from .defaults import machines_filename

    p.add_argument('--state', '-s', default=machines_filename,
                   help='Path to the machine definitions')
    p.add_argument('name', metavar='NAME', help='Name to login to')
    p.add_argument('arguments', metavar='ARG', nargs='*',
                   help='Any other arguments to the "ssh" executable')



def ssh(name, cluster, args):

    node = cluster.find_machine_by_name(name)

    cmd = ['ssh',
           '-o', 'UserKnownHostsFile=/dev/null',
           '-o', 'StrictHostKeyChecking=no',
           node.ip
    ] + args

    print ' '.join(map(quote, cmd))
    call(cmd, stderr=sys.stderr, stdout=sys.stdout)


def main(opts):
    state = State(path=opts.state)
    cluster = state.get_cluster()
    ssh(opts.name, cluster, opts.arguments)
