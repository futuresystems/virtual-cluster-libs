

import novaclient.exceptions

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
