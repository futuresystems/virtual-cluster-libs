
import logger as logging
logger = logging.getLogger(__name__)

import camel

import random
import os

import pxul.os

import traits.api as T
from traits.api import HasTraits, TraitHandler

import yaml
from easydict import EasyDict


class Provider(HasTraits):

    name = T.String()
    parameters = T.Trait(EasyDict)

    def __getattr__(self, attr):
        return getattr(self.parameters, attr)


class Cloud(HasTraits):

    name = T.String()
    parameters = T.Trait(EasyDict)

    def __getattr__(self, attr):
        return getattr(self.parameters, attr)


class Service(HasTraits):

    uuid = T.UUID()
    name = T.String()
    machines = T.Set()
    parents = T.Set()

    def __str__(self):
        return '<{} service>'.format(self.name)

    def add_machine(self, machine):
        logger.debug('Assigning %s to %s', machine.name, self.name)
        self.machines.add(machine)
        machine.services.add(self)
        for service in self.parents:
            service.add_machine(machine)


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

    uuid = T.String()
    name = T.String()
    services = T.Set(Service)
    cloud = T.Trait(Cloud)
    auth = T.Trait(Auth)
    address = AddressT()
    defaults = T.Trait(EasyDict)


    def __str__(self):
        return '<node {} on {}>'.format(self.name, self.cloud)


    def add_to(self, service):
        self.services.add(service)
        service.add_machine(self)


# internal use only
class _MachineCollection(HasTraits):
    machines = T.List(Machine)

    def assign(self, number, service):

        logger.debug('Assigning %s to %s', number, service).add()

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
            # logger.debug('Assigning %s to %s', m.name, service)
            m.add_to(service)

        logger.sub()


    def set_auth(self, auth):
        for m in self.machines:
            logger.debug('Setting auth for %s to %s', m, auth)
            m.auth = auth


    def set_cloud(self, cloudname, providers):

        if cloudname:
            for m in self.machines:
                logger.debug('Setting cloud=%s for %s', cloudname, m)
                self.cloud = Cloud(name=cloudname,
                                   parameters=providers[cloudname])
        else:
            logger.warning('No cloud defined')

    def append(self, item):
        self.machines.append(item)


    def __len__(self):
        return len(self.machines)



##################################################

class AnsibleVars(HasTraits):

    kind = T.Trait(None, 'host_vars', 'group_vars')
    vars = T.Dict() # dict string (dict string (dict string string))

    def materialize(self, cwd=None):
        """Writes out the variables to the appropriate files.

        This will completely overwrite the contents of the variables
        file.

        :param cwd: use this path as the current working directory
        """
        

        cwd = cwd or os.getcwd()
        prefix = os.path.join(cwd, self.kind)
        pxul.os.ensure_dir(prefix)

        for hostname, values in self.vars.iteritems():
            path = os.path.join(prefix, '{}.yml'.format(hostname))
            string = yaml.dump(dict(values), default_flow_style=False)
            with open(path, 'w') as fd:
                fd.write(string)


##################################################

class Cluster(HasTraits):

    uuid = T.UUID()
    provider = T.Trait(Provider)
    cloud = T.Trait(Cloud)
    machines = T.List(Machine)
    services = T.Trait(ServiceGroup)
    vars = T.List(T.Trait(AnsibleVars))


    def assign_to_cloud(self, cloudname):
        assert cloudname in self.provider.keys()

        if self.cloud is not None:
            logger.warning('Overriding previous cloud %s with %s',
                           self.cloud.name, cloudname)

        self.cloud = Cloud(name=cloudname, parameters=self.provider.parameters[cloudname])
        for m in self.machines:
            m.cloud = self.cloud


    def get_inventory_dict(self):
        """Generates the inventory as a nested dictionary

        The generated inventory adheres to the convention for dynamic
        Ansible inventories.  See here for more details:
        https://docs.ansible.com/ansible/developing_inventory.html

        :returns: the inventory
        :rtype: dict

        """
        inventory = dict()
        meta = dict(hostvars=dict())

        for servicename in self.services:
            service = self.services[servicename]
            group = dict()
            group['hosts'] = [m.name for m in service.machines]
            inventory[service.name] = group

            for machine in service.machines:
                meta['hostvars'][machine.name] = dict()

                # ansible_ssh_host
                if machine.address.external:
                    ip = machine.address.external
                else:
                    ip = machine.address.internal
                meta['hostvars'][machine.name]['ansible_ssh_host'] = ip

                # ansible_ssh_private_key
                meta['hostvars'][machine.name]['ansible_ssh_private_key'] = machine.auth.private_key

        inventory['_meta'] = meta

        return inventory



    @classmethod
    def load_yaml(cls, string):
        if os.path.exists(string):
            with open(string) as fd:
                return ClusterLoader.load_yaml(fd.read())
        else:
            return ClusterLoader.load_yaml(string)



class ClusterLoader(object):

    @classmethod
    def phase1(cls, yaml_string):
        """First pas through to load the cluster definition

        :param yaml_string: YAML-formatted string
        :returns: the cluster definition
        :rtype: Cluster
        """

        logger.debug('Running Phase 1')

        d = yaml.safe_load(yaml_string)
        d = EasyDict(d)

        provider = Provider(parameters=d.defaults.provider)
        cloud = _load_cloud(d.defaults)
        services = _load_services(d.services)
        machines = _load_machines(d.machines, services, d.defaults)
        hostvars = _load_host_vars(d.host_vars)

        cluster  = Cluster(
            provider = provider,
            cloud = cloud,
            machines = machines,
            services = services,
            vars = [hostvars],
        )

        return cluster

    
    @classmethod
    def phase2(cls, yaml_string, cluster):
        """Second pass through to expand any directives

        :param yaml_string: the YAML-formatted string
        :param cluster: context
        :returns: the cluster
        :rtype: Cluster
        """

        logger.debug('Running Phase 2')

        spec_dict = yaml.safe_load(yaml_string)

        visitor = camel.Visitor(
            handlers = [camel.env_handler],
            context  = cluster,
        )
        
        transformed = visitor.transform(spec_dict)
        new_yaml_str = yaml.dump(transformed, default_flow_style=False)
        logger.debug('New YAML:\n%s', new_yaml_str)
        return cls.phase1(new_yaml_str)


    @classmethod
    def phase3(cls, cluster):
        """Third pass through to make any final adjustments

        :param cluster: the cluster
        :returns: the modified (in place) cluster
        :rtype: Cluster
        """

        logger.debug('Running Phase 3')

        logger.debug('Assign machines to the specified cloud')
        if cluster.cloud is not None:
            cluster.assign_to_cloud(cluster.cloud.name)

        return cluster

    @classmethod
    def load_yaml(cls, yaml_string):
        cluster = cls.phase1(yaml_string)
        cluster = cls.phase2(yaml_string, cluster)
        cluster = cls.phase3(cluster)
        return cluster



##################################################


def _load_services(root):
    assert isinstance(root, dict)

    logger.info('Loading service definitions')

    group = ServiceGroup()

    for service_name in root:
        logger.debug('Defining service {}'.format(service_name))
        group[service_name] = Service(name=service_name)

    for service_name in root:
        service = group[service_name]
        if root[service_name]:
            logger.debug('Adding other services for {}'.format(service_name))
            parents = root[service_name]
            assert isinstance(parents, list)
            for parent_name in parents:
                parent = group[parent_name]
                service.parents.add(parent)
    
    return group



def _load_machines(root, services, defaults):
    logger.info('Loading machine definitions').add()

    machines = list()


    for machine_name in root:
        logger.debug('Loading definitions for {}'.format(machine_name)).add()
        collection = _MachineCollection()

        ### count
        count = root[machine_name].get('count', 1)
        for i in xrange(count):
            name = '{}{:02d}'.format(machine_name,i)            
            logger.debug('Defining machine {}'.format(name))
            collection.append(Machine(name=name))
        logger.sub()

        ### assignments
        logger.debug('Assigning machines').add()
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

        # auth
        logger.debug('Setting auth for collection %s', machine_name)
        public_key  = root[machine_name].get('public_key', defaults.auth.public_key)
        private_key = root[machine_name].get('private_key', defaults.auth.private_key)
        auth = Auth(public_key=public_key, private_key=private_key)
        collection.set_auth(auth)


        # cloud
        logger.debug('Setting cloud for collection %s', machine_name)
        cloudname = root[machine_name].get('cloud', defaults.cloud)
        collection.set_cloud(cloudname, defaults.provider)


        logger.sub()

        machines.extend(collection.machines)

    logger.sub()
    return machines


def _load_cloud(root):
    if root.cloud is None:
        return None
    else:
        assert 'name' in root.cloud.keys(), root.cloud.keys()
        assert 'parameters' in root.cloud.keys(), root.cloud.keys()
        return Cloud(name=root.cloud.name,
                     parameters=root.cloud.parameters)


def _load_host_vars(root):
    return AnsibleVars(kind='host_vars', vars=root)


def _test(path):
    c = Cluster.load_yaml(open(path).read())
    return c


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    c = _test('cluster.yaml')
    for v in c.vars:
        v.materialize()
    
