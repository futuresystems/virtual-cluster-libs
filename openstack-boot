#!/usr/bin/env python

from pprint import pprint
from openstack_lib import *
from lib import fullpath


if __name__ == '__main__':
    import sys
    import lib

    spec_path = sys.argv[1]
    out_path = sys.argv[2]
    spec = lib.read_spec(spec_path)
    machines = spec['machines']

    nova = get_client()

    for node in machines:
        print node['name']

        image_name  = lib.get_with_defaults(node, 'openstack_image', spec)
        flavor_name = lib.get_with_defaults(node, 'openstack_flavor', spec)
        key_name    = lib.get_with_defaults(node, 'openstack_key_name', spec)
        net_name    = lib.get_with_defaults(node, 'openstack_network', spec)
        sec_groups  = lib.get_with_defaults(node, 'openstack_security_groups', spec)

        try:
            nova.keypairs.find(name=key_name)
        except novaclient.exceptions.NotFound:
            path = lib.get_with_defaults(node, 'openstack_public_key', spec)
            pubkey = open(fullpath(path)).read()
            nova.keypairs.create(key_name, pubkey)

        image = nova.images.find(name=image_name)
        flavor = nova.flavors.find(name=flavor_name)
        nic = nova.networks.find(label=net_name)
        nics = [{'net-id': nic.id}]


        ################################################## boot

        try:
            nova.servers.find(name=node['name'])
            print 'Skipping'
            continue
        except novaclient.exceptions.NotFound:

            vm = nova.servers.create(
                node['name'],
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

        try:
            floating_ip = nova.floating_ips.findall(instance_id=None)[0]
        except IndexError:
            pool = lib.get_with_defaults(node,
                                         'openstack_floating_ip_pool',
                                         spec)
            floating_ip = nova.floating_ips.create(pool=pool)
        node['ip'] = str(floating_ip.ip)

        vm.add_floating_ip(floating_ip)
        node['floating_ip'] = str(floating_ip.ip)


        ################################################## internal ip

        instance = nova.servers.get(vm.id)
        addresses = instance.addresses[net_name]
        fixed_addresses = [
            a['addr']
            for a in addresses
            if a['OS-EXT-IPS:type'] == 'fixed'
        ]
        assert len(fixed_addresses) == 1
        internal_ip = fixed_addresses[0]
        node['internal_ip'] = str(internal_ip)
        

        ################################################## extra disks

        if 'extra_disks' in node:
            # cinder not yet supported
            del node['extra_disks']


        with open(out_path, 'w') as fd:
            import yaml
            fd.write(yaml.dump(spec, default_flow_style=False))
