

from vcl.boot import openstack
from vcl.boot import libvirt

__BOOTERS = dict(
    openstack = openstack,
    libvirt = libvirt
)


def main(spec, target, *args, **kws):
    global __BOOTERS

    module = __BOOTERS[target]
    module.main(spec, *args, **kws)
