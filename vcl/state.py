#
# This module provides an api for tracking the state of the virtual
# cluster.
#
# This supports:
# - recovery during boot process (previously booted machines are not regenerated)
#


import logger as logging
logger = logging.getLogger(__name__)

import os.path
import shelve

import traits.api as T
from traits.api import HasTraits

import pxul.os


class State(HasTraits):
    """State provides a single-namespace-separated key/value persistent
    store.  Values are saved by key under a specified namespace.
    Namespaces cannot be nested.
    """

    path = T.File()

    def __init__(self, *args, **kwargs):
        super(State, self).__init__(*args, **kwargs)
        self.path = pxul.os.fullpath(self.path)
        pxul.os.ensure_dir(os.path.dirname(self.path))
        self._store = shelve.open(self.path)


    def _set(self, namespace, keyfn, item):
        """Sets a value into the store

        :param namespace:
        :type namespace: str
        :param keyfn: a 0-ary function returning the key for the item
        :type keyfn: () -> str
        :param item: a pickle-able value
        """

        if namespace not in self._store.keys():
            logger.debug('Creating namespace %s', namespace)
            self._store[namespace] = dict()

        key = keyfn()

        logger.debug('Saving state %s.%s', namespace, key)

        if key in self._store[namespace]:
            logger.warn('%s.%s already stored, overwriting',
                        namespace, key)

        space = self._store[namespace]
        space[key] = item
        self._store[namespace] = space
        self._store.sync()


    def _has_key(self, namespace, key):
        """Query the store to check if it contains a desired object

        :param namespace: 
        :param key: 
        :returns: True or False
        :rtype: bool
        """
        return  namespace in self._store \
            and key in self._store[namespace]


    def set_machine(self, machine):
        """Add a machine to the store.
        Overrides a preexisting machine

        :param machine:
        :type machine: :py:class:`Machine`
        """
        self._set('machines', lambda: machine.uuid, machine)


    def has_machine(self, uuid):
        """Query if the store contains a machine with the given UUID

        :param uuid:
        :type uuid: :py:ref:`str`
        :returns: True or False
        :rtype: :py:class:`bool`

        """
        return self._has_key('machines', uuid)
