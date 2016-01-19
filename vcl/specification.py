
import traits.api as T
from traits.api import HasTraits, TraitHandler
import argparse

class Namespace(TraitHandler):

    def validate(self, object, name, value):
        if isinstance(value, argparse.Namespace):
            return value
        else:
            self.error(object, name, value)


class IPv4(TraitHandler):

    def _components(self, value):
        parts = value.split('.')
        if len(parts) != 4:
            return False, parts

        asints = map(int, parts)
        for part in asints:
            if not 0 <= part <= 255:
                return False, part

        return True, value


    def validate(self, object, name, value):
        pred, _ = self._components(value)
        if pred:
            return value

        else:
            self.error(object, name, value)

    def info(self):
        return "**an IPv4 address**"


def mk_node_class(provider, spec):
    """str -> Namespace -> type

    Construct the Node type with default values provided in the
    specification. This will automatically create subclasses of `Node`
    based on the provider (eg 'libvirt', 'openstack', etc)

    """

    class Node(HasTraits):
        hostname = T.String()
        ip = T.Trait(IPv4())
        netmask = T.Trait(spec.defaults.netmask, IPv4())
        public_key = T.String(spec.defaults.public_key)
        domain_name = T.String(spec.defaults.domain_name)
        extra_disks = T.Dict(vars(spec.defaults.extra_disks))
    clazz = Node

    if provider == 'libvirt':
        class LibvirtNode(Node):
            cpus = T.Int(spec.defaults.libvirt.cpus)
            memory = T.Int(spec.defaults.libvirt.memory)
        clazz = LibvirtNode

    elif provider == 'openstack':
        cloudname = spec.defaults.openstack_cloud
        parms = getattr(spec.defaults, cloudname)

        class OpenstackNode(Node):
            flavor = T.String(parms.flavor)
            image = T.String(parms.image)
            key_name = T.String(parms.key_name)
            network = T.String(parms.network)
            assign_floating_ip = T.Bool(parms.assign_floating_ip)
            security_groups = T.ListStr(parms.security_groups)
        clazz = OpenstackNode

    elif provider == 'vagrant':
        class VagrantNode(Node):
            provider = spec.defaults.vagrant.provider
            box = spec.defaults.vagrant.box
        clazz = VagrantNode

    else:
        raise NotImplementedError, provider

    return clazz


def mk_nodes(provider, spec):
    """str -> Namespace -> [Node]
    
    Construct the appropriate Node instances for a provider given a
    specification.
    """

    clazz = mk_node_class(provider, spec)

    def mk():
        for mach in spec.machines:
            assert len(mach) == 1, mach
            assert isinstance(mach, dict)

            node = clazz()
            hostname, params = mach.items()[0]
            assert isinstance(hostname, str)
            assert isinstance(params, dict)

            node.hostname = hostname
            for name, value in params.iteritems():

                if name == provider:
                    assert isinstance(value, dict)

                    for k,v in value.iteritems():
                        setattr(node, k, v)

                else:
                    setattr(node, name, value)
                        
            yield node

    return list(mk())


def mk_namespace(spec_dict):
    """dict -> Namespace

    Provides a nice dotted attribute access to the elements of a
    dictionary.

    eg:
    >>> s = mk_namespace({'foo':{'bar': 42}, baz = 24})
    >>> s.foo.bar
    42
    >>> s.baz
    24
    """

    def mk(obj):
        for k in obj.iterkeys():
            v = obj[k]
            if isinstance(v, dict):
                obj[k] = mk(obj[k])
        return argparse.Namespace(**obj)

    return mk(spec_dict)
