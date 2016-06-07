
import random

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


# internal use only
class _ServiceGroup(HasTraits):

    uuid = T.UUID()
    services = T.Dict(T.String, Service)

    def __getitem__(self, name):
        return self.services[name]

    def __setitem__(self, k, v):
        self.services[k] = v


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
    vars = T.Dict()


##################################################

class Cluster(HasTraits):

    uuid = T.UUID()
    provider = T.Trait(Provider)
    machines = T.Dict(T.String(), T.Trait(Machine))  # name -> Machine
    services = T.Dict(T.String(), T.Trait(Service))  # name -> Service
    vars = T.List(T.Trait(AnsibleVars))


    @classmethod
    def load_yaml(cls, path):

        with open(path) as fd:
            d = yaml.load(fd)
            d = EasyDict(d)

        services = _load_services(d.services)
        machines = _load_machines(d.machines, services)
        hostvars = _load_host_vars(d.host_vars)

        cluster  = cls(
            machines = dict([(m.name, m) for m in machines]),
            services = services,
            vars = [hostvars],
        )

        return cluster

##################################################


def _load_services(root):
    group = _ServiceGroup()

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

    return group.services



def _load_machines(root, services):

    machines = list()


    for machine_name in root:
        collection = _MachineCollection()

        ### count
        count = root[machine_name].get('count', 1)
        for i in xrange(count):
            collection.append(Machine(name='{}{:02d}'.format(machine_name,i)))

        ### assignments
        assignments = root[machine_name].get('for', [])
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
    c = Cluster.load_yaml(path)
    return c
