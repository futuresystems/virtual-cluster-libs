"""
List running VMs
"""

from __future__ import absolute_import

from vcl.specification import load_machines


def add_parser(p):

    from .defaults import machines_filename

    p.add_argument('--machines', '-m', metavar='FILE',
                   default=machines_filename,
                   help='Path to the machines file')



def main(opts):

    machines = load_machines(opts.machines)

    for hostname in machines:
        print hostname
