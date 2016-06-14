#
# This module provides an api for tracking the state of the virtual
# cluster.  This allows for recovery if the booting process fails.
#


import logger as logging
logger = logging.getLogger(__name__)

import os.path

import traits.api as T
from traits.api import HasTraits

import yaml


class State(HasTraits):

    storage = T.File()
    state = T.DictStrAny()

    def _read(self):
        if os.path.exists(self.storage):
            logger.debug('Reading state from %s', self.storage)
            with open(self.storage) as fd:
                return yaml.safe_load(fd)
        else:
            logger.debug('Creating in-memory state object')
            return dict()


    def _write(self):
        logger.debug('Writing state to %s', self.storage)
        string = yaml.dump(self.state, default_flow_style=False)
        with open(self.storage, 'w') as fd:
            fd.write(string)


    def _set(self, namespace, item):
        logger.debug('Saving state for %s', item)
        assert item.uuid is not None

        self._read()

        if item.uuid in self.state:
            logger.warn('%s already stored, overwriting', item)

        self.state[namespace] = item

        self._write()


    def set_machine(self, machine):
        self._set('machines', machine)
