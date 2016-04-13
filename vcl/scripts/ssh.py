"""
Ssh into a machines
"""

from __future__ import absolute_import

from vcl.specification import load_machines

def add_parser(p):

    from .defaults import machines_filename

    p.add_argument('--machines', '-m', default=machines_filename,
                   help='Path to the machine definitions file')
    p.add_argument('hostname', metavar='HOST', help='Hostname to login to')
    p.add_argument('arguments', metavar='ARG', nargs='*',
                   help='Any other arguments to the "ssh" executable')



def ssh(hostname, machines, args):

    from subprocess import call
    import sys
    from pipes import quote

    node = machines[hostname]
    if hasattr(node, 'floating_ip') and node.floating_ip is not None:
        ip = node.floating_ip
    else:
        ip = node.ip

    cmd = ['ssh',
           '-o', 'UserKnownHostsFile=/dev/null',
           '-o', 'StrictHostKeyChecking=no',
           ip
    ] + args

    print ' '.join(map(quote, cmd))
    call(cmd, stderr=sys.stderr, stdout=sys.stdout)


def main(opts):
    machines = load_machines(opts.machines)
    ssh(opts.hostname, machines, opts.arguments)
