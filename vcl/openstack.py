
import novaclient
import novaclient.exceptions

from pxul.os import fullpath
import sys


# ignore the urllib3 SecurityWarnings
# https://github.com/shazow/urllib3/issues/497
import warnings
warnings.simplefilter('ignore')


def get_client():
    from keystoneclient.session import Session
    from novaclient.client import Client
    from os import getenv as ge
    from keystoneclient.auth.identity import Password


    OS_AUTH_URL = ge('OS_AUTH_URL')

    if OS_AUTH_URL.endswith('v2.0'):
        auth = Password(
            ge('OS_AUTH_URL'),
            username=ge('OS_USERNAME'),
            password=ge('OS_PASSWORD'),
            tenant_name=ge('OS_TENANT_NAME')
        )
    elif OS_AUTH_URL.endswith('v3'):
        auth = Password(
            ge('OS_AUTH_URL'),
            username=ge('OS_USERNAME'),
            password=ge('OS_PASSWORD'),
            user_domain_id=ge('OS_USER_DOMAIN_ID', 'default'),
            project_domain_id=ge('OS_PROJECT_DOMAIN_ID', 'default'),
            project_name=ge('OS_PROJECT_NAME'),
        )
    else:
        raise ValueError('Unable to discover version from {}'.format(OS_AUTH_URL))


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


def wait_until(expr, sleep_time=1, max_time=60):
    import time
    slept = 0
    while not expr():
        msg = '{} / {}'.format(slept+sleep_time, max_time)
        sys.stdout.write(msg)
        sys.stdout.flush()
        sys.stdout.write('\b' * len(msg))
        time.sleep(sleep_time)
        slept += sleep_time
        if slept >= max_time:
            print(msg + ' Timed out')
            raise RuntimeError, 'Timeout while waiting for {}'.format(expr)
    print(msg + '...done')



def boot(nodes, prefix='', dry_run=False,
         waitForActiveSleep=1,
         waitForActiveTimeout=60,
         **kws):

    nova = get_client()

    for node in nodes:
        node_name = prefix + node.hostname
        print node.hostname, '->', node_name

        image_name = node.image
        flavor_name = node.flavor
        key_name = node.key_name
        net_name = node.network
        sec_groups = node.security_groups

        if dry_run:
            yield node
            continue

        ################################################## upload key if needed

        try:
            print('-> Looking for key {}'.format(key_name))
            nova.keypairs.find(name=key_name)
        except novaclient.exceptions.NotFound:
            print('...not found, adding {} as {}'.format(node.public_key, key_name))
            path = node.public_key
            key  = open(fullpath(path)).read()
            nova.keypairs.create(key_name, key)

        image = nova.images.find(name=image_name)
        flavor = nova.flavors.find(name=flavor_name)
        nics = [{'net-id': nova.networks.find(label=net_name).id}]


        ################################################## boot

        try:
            print('-> Checking if already booted')
            nova.servers.find(name=node_name)
            print '...true'
            continue
        except novaclient.exceptions.NotFound:

            print('-> Creating {}'.format(node_name))
            vm = nova.servers.create(
                node_name,
                image,
                flavor,
                key_name=key_name,
                nics=nics
            )

        def is_active():
            instance = nova.servers.get(vm.id)
            return instance.status == 'ACTIVE'

        print '-> Waiting until ACTIVE ',
        wait_until(is_active, sleep_time=waitForActiveSleep, max_time=waitForActiveTimeout)


        ################################################## security groups

        for name in sec_groups:
            print('-> Adding to security group {}'.format(name))
            vm.add_security_group(name)


        ################################################## floating ip

        if node.create_floating_ip:
            print('-> Adding floating ip')
            try:
                # first try to get a free ip
                floating_ip = nova.floating_ips.findall(instance_id=None)[0]
                print('...using {}'.format(floating_ip))
            except IndexError:
                pool = node.floating_ip_pool
                floating_ip = nova.floating_ips.create(pool=pool)
                print('...allocated {} from pool {}'.format(floating_ip, pool))

            print('...associating')
            vm.add_floating_ip(floating_ip)

            # usefull for regenerating a spec file
            node.floating_ip = floating_ip.ip
            # node.set_dynamic('floating_ip', str(ip.ip))
            print('...done')


        ################################################## internal ip

        print('-> Geting internal ip')
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
        print('...done')

        ################################################## extra discs

        for disk in node.extra_disks:
            # cinder not support yet
            print 'WARNING extra disks not supported yet'
            # node.unset_dynamic('extra_disks')


        ################################################## save
        yield node
