

from pprint import pprint
from vcl.util.openstack import get_client, find_by_query, wait_until

def main(spec, provider, **kws):

    machines = spec.machines
    cloud = spec.defaults.openstack_cloud

    nova = get_client()

    for node in machines:
        print node['name']

        image_name = node.openstack.image()
        flavor_name = node.openstack.flavor()
        key_name = node.openstack.key_name()
        net_name = node.openstack.network()
        sec_groups = node.openstack.security_groups()

        try:
            nova.keypairs.find(name=key_name)
        except novaclient.exceptions.NotFound:
            path = node.public_key()
            key  = open(fullpath(path)).read()
            nova.keypairs.create(key_name, key)

        image = nova.images.find(name=image_name)
        flavor = nova.flavors.find(name=flavor_name)
        nics = [{'net-id': nova.networks.find(label=net_name).id}]


        ################################################## boot

        try:
            nova.servers.find(name=node.name)
            print 'Already booted'
            continue
        except novaclient.exceptions.NotFound:

            vm = nova.servers.create(
                nova.name,
                image,
                flavor,
                key_name=key_name,
                nics=nics
            )

        def is_active():
            instance = nova.servers.get(vm.id)
            return instance.status == 'ACTIVE'

        wait_until(is_active)


        ################################################## security groups

        for name in sec_groups:
            vm.add_security_group(name)


        ################################################## floating ip

        if node.openstack.assign_floating_ip():
            try:
                # first try to get a free ip
                floating_ip = nova.floating_ips.findall(instance_id=None)[0]
            except IndexError:
                pool = nova.openstack.floating_ip_pool()
                ip = nova.floating_ips.create(pool=pool)

            # usefull for regenerating a spec file
            node.set_dynamic('floating_ip', str(ip.ip))

            vm.add_floating_ip(ip)


        ################################################## extra discs

        for disk in node.extra_disks():
            # cinder not support yet
            print 'WARNING extra disks not supported yet'
            node.unset_dynamic('extra_disks')


        ################################################## save
