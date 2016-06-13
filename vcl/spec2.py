
import parser
from parser import Parser
import logger as logging

logger = logging.getLogger(__name__)

import random
import copy
import operator


import traits.api as T
from traits.api import HasTraits, TraitHandler

import yaml
from easydict import EasyDict


class Provider(HasTraits):

    uuid = T.UUID()
    name = T.String()


class Service(HasTraits):

    uuid = T.UUID()
    name = T.String()
    machines = T.Set()
    parents = T.Set()

    def __str__(self):
        return '<{} service>'.format(self.name)

    def add_machine(self, machine):
        self.machines.add(machine)
        machine.services.add(self)


class ServiceGroup(HasTraits):

    uuid = T.UUID()
    services = T.Dict(T.String, Service)

    def __getitem__(self, name):
        return self.services[name]

    def __setitem__(self, k, v):
        self.services[k] = v

    def __getattr__(self, attr):
        return self.services[attr]

    def __len__(self):
        return len(self.services)

    def __iter__(self):
        return iter(self.services)


class IPv4TraitHandler(TraitHandler):

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


class AddressT(HasTraits):
    internal = T.Trait(IPv4TraitHandler())
    external = T.Trait(IPv4TraitHandler())


class Auth(HasTraits):
    public_key = T.File()
    private_key = T.File()



class Machine(HasTraits):

    uuid = T.UUID()
    name = T.String()
    services = T.Set(Service)
    provider = T.Trait(Provider)
    auth = T.Trait(Auth)
    address = AddressT()
    defaults = T.Trait(EasyDict)


    def __str__(self):
        return '<node {} on {}>'.format(self.name, self.provider)


    def add_to(self, service):
        self.services.add(service)
        service.machines.add(self)


# internal use only
class _MachineCollection(HasTraits):
    machines = T.List(Machine)

    def assign(self, number, service):

        if number < len(self):
            subset = random.sample(self.machines, number)

        elif number == len(self):
            subset = self.machines

        else:
            msg = ('Cannot allocate more machines ({}) '
                   'than are in the group ({}).')\
                  .format(number, len(self.machines))
            raise ValueError(msg)

        for m in subset:
            m.add_to(service)


    def append(self, item):
        self.machines.append(item)


    def __len__(self):
        return len(self.machines)



##################################################

class AnsibleVars(HasTraits):

    kind = T.Trait(None, 'host_vars', 'group_vars')
    vars = T.Dict() # dict string (dict string (dict string string))

    # def materialize(self, cwd=None):
    #     cwd = cwd or os.getcwd()
    #     prefix = os.path.join(cwd, self.kind)
    #     pxul.os.ensure_dir(prefix)

    #     for service_name in self.vars['services']


##################################################

class Cluster(HasTraits):

    uuid = T.UUID()
    provider = T.Trait(Provider)
    machines = T.List(Machine)
    services = T.Trait(ServiceGroup)
    vars = T.List(T.Trait(AnsibleVars))

    @classmethod
    def load_yaml(cls, yaml_string):
        return ClusterLoader.load_yaml(yaml_string)


class ClusterLoader(object):

    @classmethod
    def phase1(cls, yaml_string):

        d = yaml.safe_load(yaml_string)
        d = EasyDict(d)

        services = _load_services(d.services)
        machines = _load_machines(d.machines, services)
        hostvars = _load_host_vars(d.host_vars)

        cluster  = Cluster(
            machines = machines,
            services = services,
            vars = [hostvars],
        )

        return cluster

    
    @classmethod
    def phase2(cls, yaml_string, cluster):

        spec_dict = yaml.safe_load(yaml_string)

        visitor = SpecificationVisitor(
            handlers = [parser.env_handler],
            context  = cluster,
        )
        
        transformed = visitor.transform(spec_dict)
        new_yaml_str = yaml.dump(transformed, default_flow_style=False)
        logger.debug('New YAML:\n%s', new_yaml_str)
        return cls.phase1(new_yaml_str)


    @classmethod
    def load_yaml(cls, yaml_string):
        cluster = cls.phase1(yaml_string)
        cluster = cls.phase2(yaml_string, cluster)
        return cluster


class SpecificationVisitor(HasTraits):

    handlers = T.List()
    context  = T.Trait(Cluster)


    def _getSymbolBy(self, getter, instance, symbol):
        names = symbol.split('.')
        i = instance
        for name in names:
            if not name: break
            i = getter(i, name)
        return i

    def _getObjectSymbol(self, obj, symbol):
        return self._getSymbolBy(getattr, obj, symbol)


    def _getDictSymbol(self, dictionary, symbol):
        return self._getSymbolBy(operator.getitem, dictionary, symbol)


    def _getSymbol(self, value, symbol):
        if isinstance(value, dict):
            return self._getDictSymbol(value, symbol)
        else:
            return self._getObjectSymbol(value, symbol)


    def transform(self, spec):
        self.spec = copy.deepcopy(spec)
        return self.visit(self.spec)


    def visit_generic(self, node):
        return node


    def visit(self, node):
        typ  = type(node).__name__
        attr = 'visit_{}'.format(typ)
        visitor = getattr(self, attr, self.visit_generic)
        logger.debug('Visiting type={} method={}'.format(typ, visitor.func_name))
        logger.debug('Value="{}"'.format(repr(node)))
        return visitor(node)


    def transform_dict(self, node, key):


        logger.debug('Transforming dict key: {}'.format(key))

        ### don't use pyparsing's addParseAction as this causes
        ### bizarre errors (likely due to some pyparsing
        ### statefullness)


        p = Parser()
        parsed = p.keyword.parseString(key)
        logger.debug('Parsed items: {}'.format(parsed.items()))
        
        if parsed.directive == 'inherit':
            # This replaces the <<inherits:...>> keyword with the target.

            spec = self._getDictSymbol(self.spec, parsed.symbol)
            spec = copy.copy(spec)
            del node[key]
            for k, v in node.iteritems():
                spec[k] = v

            for k, v in spec.iteritems():
                node[k] = v


        elif parsed.directive == 'index':
            seq = self._getObjectSymbol(self.context, parsed.symbol)

            for variable in node[key].keys():
                for i, val in enumerate(seq, parsed.index):
                    k = self._getSymbol(val, parsed.attribute)
                    if k not in node:
                        node[k] = dict()
                    node[k][variable] = i
            del node[key]


        elif parsed.directive == 'forall':
            seq = self._getObjectSymbol(self.context, parsed.symbol)

            for variable, value in node[key].iteritems():
                for val in seq:
                    k = self._getSymbol(val, parsed.attribute)
                    if k not in node:
                        node[k] = dict()
                    node[k][variable] = value
            del node[key]

        else:
            logger.error('Unable to handle directive "{}"'.format(parsed.directive))
            raise ValueError("I don't know how to handle directive {}"
                             .format(parsed.directive))


    def visit_dict(self, node):

        seen = set()

        logger.debug('Visiting dict keys')
        while True:
            keys = set(node.keys())

            try:
                k = keys.difference(seen).pop()
            except KeyError:
                break

            logger.debug('Processing key "{}"'.format(k))
            if k.startswith('<<') and k.endswith('>>'):
                self.transform_dict(node, k)
            seen.add(k)


        logger.debug('Visiting dict values')
        for k in node:
            logger.add()
            node[k] = self.visit(node[k])
            logger.sub()

        return node


    def visit_list(self, node):
        for i in xrange(len(node)):
            logger.add()
            node[i] = self.visit(node[i])
            logger.sub()
        return node


    def visit_str(self, node):
        return Parser.transform('expansion', self.handlers, node)


##################################################


def _load_services(root):
    group = ServiceGroup()

    for service_name in root:
        group[service_name] = Service(name=service_name)

    for service_name in root:
        service = group[service_name]
        if root[service_name]:
            parents = root[service_name]
            assert isinstance(parents, list)
            for parent_name in parents:
                parent = group[parent_name]
                service.parents.add(parent)

    return group



def _load_machines(root, services):

    machines = list()


    for machine_name in root:
        collection = _MachineCollection()

        ### count
        count = root[machine_name].get('count', 1)
        for i in xrange(count):
            collection.append(Machine(name='{}{:02d}'.format(machine_name,i)))

        ### assignments
        assignments = root[machine_name].get('services', [])
        for service_name in assignments:
            service = services[service_name]

            node = assignments[service_name]
            howmany_default = len(collection)
            if node:
                how_many = node.get('assign', howmany_default)
            else:
                how_many = howmany_default

            collection.assign(how_many, service)

        machines.extend(collection.machines)
    return machines


def _load_host_vars(root):
    return AnsibleVars(kind='host_vars', vars=root)


def _test(path):
    c = Cluster.load_yaml(open(path).read())
    return c


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    _test('cluster.yaml')
