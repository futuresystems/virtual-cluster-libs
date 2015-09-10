#!/usr/bin/env python

import yaml
import os.path


def fullpath(path):
    from os.path import abspath, expanduser, expandvars
    return abspath(expanduser(expandvars(path)))


def read_spec(path):
    with open(path) as fd:
        return yaml.load(fd)


def get_with_defaults(definition, attr, spec):
    return definition.get(attr, spec['defaults'].get(attr))


def build_inventory_mapping(spec):
    name_to_node = {}
    for machine in spec['machines']:
        assert machine['name'] not in name_to_node
        name_to_node[machine['name']] = machine

    return name_to_node

def inventory(spec):
    # the virtual group is used to preserve order in the generated
    # inventory file
    name_to_node = build_inventory_mapping(spec)
    for virtual_group in spec['inventory']:
        for groupname, group in virtual_group.iteritems():
            nodes = [name_to_node[name] for name in group]
            yield groupname, nodes
