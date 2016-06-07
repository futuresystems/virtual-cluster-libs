
import parser

import random
import copy
from functools import partial
import collections

import traits.api as T
from traits.api import HasTraits

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


class Machine(HasTraits):

    uuid = T.UUID()
    name = T.String()
    services = T.Set(Service)
    provider = T.Trait(Provider)


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
    machines = T.Dict(T.String(), T.Trait(Machine))  # name -> Machine
    services = T.Trait(ServiceGroup)
    vars = T.List(T.Trait(AnsibleVars))

    # @classmethod
    # def load_yaml(cls, yaml_string, expand=True):


        # visitor = parser.Visitor(
        #     handlers = [parser.env_handler,
        #                 parser.index_handler],
        #     context  = cluster,
        # )
        # d2 = visit(d)

        # return cluster


class ClusterLoader(object):

    @classmethod
    def phase1(cls, yaml_string):

        d = yaml.load(yaml_string)
        d = EasyDict(d)

        services = _load_services(d.services)
        machines = _load_machines(d.machines, services)
        hostvars = _load_host_vars(d.host_vars)

        cluster  = Cluster(
            machines = dict([(m.name, m) for m in machines]),
            services = services,
            vars = [hostvars],
        )

        return cluster

    
    @classmethod
    def phase2(cls, yaml_string, cluster):

        spec_dict = yaml.load(yaml_string)

        visitor = SpecificationVisitor(
            handlers = [parser.env_handler,
                        partial(parser.index_handler, cluster)],
        )
        
        transformed = visitor.transform(spec_dict)
        new_yaml_str = yaml.dump(transformed)
        return cls.phase1(new_yaml_str)


    @classmethod
    def load_yaml(cls, yaml_string):
        cluster = cls.phase1(yaml_string)
        cluster = cls.phase2(yaml_string, cluster)
        return cluster


class SpecificationVisitor(HasTraits):

    handlers = T.List()


    def transform(self, spec):
        self.spec = copy.deepcopy(spec)
        return self.visit(self.spec)


    def visit_generic(self, node):
        return node


    def visit(self, node):
        typ  = type(node).__name__
        attr = 'visit_{}'.format(typ)
        visitor = getattr(self, attr, self.visit_generic)
        return visitor(node)


    def visit_dict(self, node):
        inherit = '<inherit>'
        if inherit in node:
            name = node[inherit]
            path = name.split('.')
            new  = self.spec
            for key in path:
                new = new[key]
            del node['<inherit>']
            for k,v in node.iteritems():
                new[k] = v
            node = new

        for k in node.keys():
            node[k] = self.visit(node[k])

        return node


    def visit_list(self, node):
        for i in xrange(len(node)):
            node[i] = self.visit(node[i])
        return node


    def visit_str(self, node):
        print node
        return parser.transform(parser.expansion, self.handlers, node)


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


def test(path):
    c = ClusterLoader.load_yaml(open(path).read())
    return c
