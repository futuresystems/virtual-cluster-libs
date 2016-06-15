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
import pickle

import traits.api as T
from traits.api import HasTraits

import pxul.os


class State(HasTraits):
    """State provides a single-namespace-separated key/value persistent
    store.  Values are saved by key under a specified namespace
    separated by forward slashes (/).

    """

    path = T.Directory()

    def __init__(self, *args, **kwargs):
        super(State, self).__init__(*args, **kwargs)
        self.path = pxul.os.fullpath(self.path)
        pxul.os.ensure_dir(self.path)


    def _set(self, namespace, keyfn, item):
        """Sets a value into the store

        :param namespace:
        :type namespace: str
        :param keyfn: a 0-ary function returning the key for the item
        :type keyfn: () -> str
        :param item: a pickle-able value
        """

        pxul.os.ensure_dir(os.path.join(self.path, namespace))

        key = os.path.join(self.path, namespace, keyfn())

        logger.debug('Saving state %s', key)

        if os.path.exists(key):
            logger.warn('%s already stored, overwriting', key)

        with open(key, 'wb') as fd:
            pickle.dump(item, fd)


    def _get(self, namespace, keyfn):

        key = os.path.join(self.path, namespace, keyfn())
        logger.debug('Getting %s', key)

        with open(key, 'rb') as fd:
            return pickle.load(fd)


    def _has_key(self, namespace, key):
        """Query the store to check if it contains a desired object

        :param namespace: 
        :param key: 
        :returns: True or False
        :rtype: bool
        """
        return os.path.exists(os.path.join(self.path, namespace, key))


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


    def set_cluster(self, cluster):
        """Store the current state of the cluster

        :param cluster: the cluster to store
        :type cluster: :py:class:`Cluster`
        """
        self._set('cluster', lambda: 'cluster.dat', cluster)


    def get_cluster(self):
        return self._get('cluster', lambda: 'cluster.dat')
