
import logger as logging
logger = logging.getLogger(__name__)

from state import State


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



def boot(cluster, dry_run=False, **kws):

    nova = get_client()
    state = State(storage='.machines')

    logger.mem_save('boot')

    for node in cluster.machines:
        node_name = cluster.cloud.prefix + node.name
        logger.mem('boot').info('Booting %s as %s on %s', node.name, node_name, node.cloud.name).add()

        image_name = node.cloud.image
        flavor_name = node.cloud.flavor
        key_name = node.cloud.key_name
        net_name = node.cloud.network
        sec_groups = node.cloud.security_groups

        if dry_run:
            continue

        ################################################## upload key if needed

        try:
            logger.info('Looking for key %s', key_name)
            nova.keypairs.find(name=key_name)
        except novaclient.exceptions.NotFound:
            logger.info('...not found, adding %s as %s',
                        node.public_key, key_name)
            path = node.public_key
            key  = open(fullpath(path)).read()
            nova.keypairs.create(key_name, key)

        image = nova.images.find(name=image_name)
        flavor = nova.flavors.find(name=flavor_name)
        nics = [{'net-id': nova.networks.find(label=net_name).id}]


        ################################################## boot

        try:
            logger.info('Checking if already booted')
            nova.servers.find(name=node_name)
            logger.info('...true')
            continue
        except novaclient.exceptions.NotFound:

            logger.info('Creating %s', node_name)
            vm = nova.servers.create(
                node_name,
                image,
                flavor,
                key_name=key_name,
                nics=nics
            )
            node.uuid = vm.id

        def is_active():
            instance = nova.servers.get(vm.id)
            return instance.status == 'ACTIVE'

        logger.info('Waiting until ACTIVE ')
        wait_until(is_active,
                   sleep_time=cluster.cloud.parameters.poll_until_active_seconds,
                   max_time=cluster.cloud.parameters.timeout_until_active_seconds)


        ################################################## security groups

        for name in sec_groups:
            logger.info('Adding to security group %s', name)
            vm.add_security_group(name)


        ################################################## floating ip

        if node.cloud.create_floating_ip:
            logger.info('Adding floating ip')
            try:
                # first try to get a free ip
                floating_ip = nova.floating_ips.findall(instance_id=None)[0]
                logger.info('...using %s', floating_ip)
            except IndexError:
                pool = node.cloud.floating_ip_pool
                floating_ip = nova.floating_ips.create(pool=pool)
                logger.info('...allocated %s from pool %s', floating_ip, pool)

            logger.info('...associating')
            vm.add_floating_ip(floating_ip)

            node.address.external = floating_ip
            logger.info('...done')


        ################################################## internal ip

        logger.info('Getting internal ip')
        instance = nova.servers.get(vm.id)
        addresses = instance.addresses[net_name]
        fixed_addresses = [
            a['addr']
            for a in addresses
            if a['OS-EXT-IPS:type'] == 'fixed'
        ]
        assert len(fixed_addresses) == 1, fixed_addresses
        internal_ip = fixed_addresses[0]
        node.address.internal = internal_ip
        logger.info('...done')

        ################################################## extra discs

        for disk in node.extra_disks:
            # cinder not support yet
            print 'WARNING extra disks not supported yet'
            # node.unset_dynamic('extra_disks')


        ################################################## save
        state.set_machine(node)
