
import logger as logging
logger = logging.getLogger(__name__)

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
    parser.add_argument('-v', '--verbose', action='count',
                        help='Verbosity level, repeat for increased verbosity')

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
    set_verbosity_level(opts)
    opts.func(opts)


def set_verbosity_level(opts):
    if not opts.verbose:
        logging.basicConfig(level=logging.CRITICAL)
    elif opts.verbose == 1:
        logging.basicConfig(level=logging.WARNING)
    elif opts.verbose == 2:
        logging.basicConfig(level=logging.INFO)
    elif opts.verbose >= 3:
        logging.basicConfig(level=logging.DEBUG)
    else:
        raise ValueError('Verbosity cannot be < 0: %s' % opts.verbose)


if __name__ == '__main__':
    main()
