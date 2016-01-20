
import novaclient
import novaclient.exceptions

from pxul.os import fullpath


# ignore the urllib3 SecurityWarnings
# https://github.com/shazow/urllib3/issues/497
import warnings
warnings.simplefilter('ignore')


def get_client():
    from keystoneclient.auth.identity.v3 import Password
    from keystoneclient.session import Session
    from novaclient.client import Client
    from os import getenv as ge

    auth = Password(
        auth_url=ge('OS_AUTH_URL'),
        username=ge('OS_USERNAME'),
        password=ge('OS_PASSWORD'),
        user_domain_id=ge('OS_USER_DOMAIN_ID', 'default'),
        project_domain_id=ge('OS_PROJECT_DOMAIN_ID', 'default'),
        project_name=ge('OS_PROJECT_NAME', ge('OS_TENANT_NAME')),
    )
    
    session = Session(
        auth=auth,
        verify=ge('OS_CACERT'),
    )

    client = Client('2', session=session)
    return client



def find_by_query(objects, ident, query='name'):
    objects = [
        obj for obj in objects
        if getattr(obj, query) == ident
    ]

    assert len(objects) == 1
    return objects[0]


def wait_until(expr, sleep_time=1, max_time=30):
    import time
    slept = 0
    while not expr():
        time.sleep(sleep_time)
        slept += sleep_time
        if slept >= max_time:
            break



def boot(nodes, **kws):

    nova = get_client()

    for node in nodes:
        print node.hostname

        image_name = node.image
        flavor_name = node.flavor
        key_name = node.key_name
        net_name = node.network
        sec_groups = node.security_groups

        ################################################## upload key if needed

        try:
            nova.keypairs.find(name=key_name)
        except novaclient.exceptions.NotFound:
            path = node.public_key
            key  = open(fullpath(path)).read()
            nova.keypairs.create(key_name, key)

        image = nova.images.find(name=image_name)
        flavor = nova.flavors.find(name=flavor_name)
        nics = [{'net-id': nova.networks.find(label=net_name).id}]


        ################################################## boot

        try:
            nova.servers.find(name=node.hostname)
            print 'Already booted'
            continue
        except novaclient.exceptions.NotFound:

            vm = nova.servers.create(
                node.hostname,
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

        if node.create_floating_ip:
            print 'Adding floating ip'
            try:
                # first try to get a free ip
                floating_ip = nova.floating_ips.findall(instance_id=None)[0]
            except IndexError:
                pool = node.floating_ip_pool
                floating_ip = nova.floating_ips.create(pool=pool)

            vm.add_floating_ip(floating_ip)

            # usefull for regenerating a spec file
            node.floating_ips.append(str(floating_ip.ip))
            # node.set_dynamic('floating_ip', str(ip.ip))


        ################################################## internal ip

        instance = nova.servers.get(vm.id)
        addresses = instance.addresses[net_name]
        fixed_addresses = [
            a['addr']
            for a in addresses
            if a['OS-EXT-IPS:type'] == 'fixed'
        ]
        assert len(fixed_addresses) == 1, fixed_addresses
        internal_ip = fixed_addresses[0]
        node.ip = internal_ip

        ################################################## extra discs

        for disk in node.extra_disks:
            # cinder not support yet
            print 'WARNING extra disks not supported yet'
            # node.unset_dynamic('extra_disks')


        ################################################## save
