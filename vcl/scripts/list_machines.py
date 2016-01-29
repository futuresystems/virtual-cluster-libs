
from __future__ import absolute_import

from vcl.specification import load_spec
from argparse import ArgumentParser



def getopts():

    from defaults import spec_filename

    p = ArgumentParser()
    p.add_argument('specfile', metavar='FILE', default=spec_filename)

    return p.parse_args()


def main(opts):

    spec = load_spec(opts.specfile)

    for machine in spec.machines:
        assert len(machine) == 1
        hostname = machine.keys()[0]
        print hostname


if __name__ == '__main__':
    main(getopts())
