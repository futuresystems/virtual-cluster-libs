
from vcl.specification import load_machines

def getopts():

    from defaults import machines_filename
    from argparse import ArgumentParser

    p = ArgumentParser()
    p.add_argument('--machines', '-m', default=machines_filename)
    p.add_argument('hostname', metavar='HOST')
    p.add_argument('arguments', metavar='ARG', nargs='*')

    return p.parse_args()


def ssh(hostname, machines, args):

    from subprocess import check_output
    from pipes import quote

    ip = machines[hostname].ip

    cmd = ['ssh',
           '-o', 'UserKnownHostsFile=/dev/null',
           '-o', 'StrictHostKeyChecking=no',
           ip
    ] + args

    print ' '.join(map(quote, cmd))
    print check_output(cmd)


if __name__ == '__main__':
    opts = getopts()
    machines = load_machines(opts.machines)
    ssh(opts.hostname, machines, opts.arguments)
