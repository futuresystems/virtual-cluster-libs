

from __future__ import absolute_import

import vcl.logger as logging
logger = logging.getLogger(__name__)

from vcl.state import State
from .defaults import machines_filename, inventory_filename

import sys

def add_parser(p):

    p.add_argument('-s', '--statefile', default=machines_filename,
                   help='Path to the persistent state file')

    p.add_argument('-o', '--output', default=inventory_filename,
                   help='Write inventory to this file. If - then use stdout')

    p.add_argument('-f', '--format', choices=['json', 'ini'], default='ini',
                   help='Format the inventory')


def main(opts):

    state = State(path=opts.statefile)

    try:
        cluster = state.get_cluster()
    except KeyError:
        logger.critical('The cluster is not stored persistently')
        return 1

    logger.info('Formatting inventory as %s', opts.format)
    if opts.format == 'json':
        inventory = cluster.get_inventory_json()
    elif opts.format == 'ini':
        inventory = cluster.get_inventory_ini()
    else:
        msg = 'Unsupported format {}'.format(opts.format)
        logger.critical(msg)
        raise ValueError(msg)

    if opts.output == '-':
        logger.info('Writing inventory to stdout')
        fd = sys.stdout
    else:
        logger.info('Writing inventory to %s', opts.output)
        fd = open(opts.output, 'w')

    fd.write(inventory)

    
