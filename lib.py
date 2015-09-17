#!/usr/bin/env python

import yaml
import os.path
import itertools


def concat_uniq(lists):

    def uniqify():
        seen = set()
        for a in itertools.chain(*lists):
            if a not in seen:
                yield a
            seen.add(a)

    return list(uniqify())


def visit(yaml_value):

    if isinstance(yaml_value, list):
        return map(visit, yaml_value)

    elif isinstance(yaml_value, dict):
        new = dict()
        for k, v in yaml_value.iteritems():

            if k == '^CONCAT^':
                assert isinstance(v, list)
                children = visit(v)
                return concat_uniq(children)

            else:
                new[k] = visit_dict(k, v)

        return new

    else:
        return yaml_value


def visit_dict(key, value):

    if key == 'CONCAT':
        assert isinstance(value, list)
        children = visit(value)
        return concat_uniq(children)
    else:
        return visit(value)


def transform(yaml_value):
    return visit(yaml_value)



def fullpath(path):
    from os.path import abspath, expanduser, expandvars
    return abspath(expanduser(expandvars(path)))


def read_spec(path):
    with open(path) as fd:
        yaml_dict = yaml.load(fd)
        t =  transform(yaml_dict)
        return t


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
