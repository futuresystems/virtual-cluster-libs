
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import collections

import vcl.scripts.boot
import vcl.scripts.list_machines
import vcl.scripts.ssh

def main():

    subcmds = collections.OrderedDict()
    subcmds['boot'] = vcl.scripts.boot
    subcmds['list'] = vcl.scripts.list_machines
    subcmds['ssh' ] = vcl.scripts.ssh


    parser = ArgumentParser() #formatter_class=ArgumentDefaultsHelpFormatter)

    subparsers = parser.add_subparsers(title='subcommands')

    for cmd, module in subcmds.iteritems():
        sub = subparsers.add_parser(
            cmd,
            description=module.__doc__,
            formatter_class=ArgumentDefaultsHelpFormatter,
        )

        module.add_parser(sub)
        sub.set_defaults(func=module.main)


    opts = parser.parse_args()
    opts.func(opts)


if __name__ == '__main__':
    main()
