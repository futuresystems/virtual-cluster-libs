

import yaml
from traits.api import HasTraits, DictStrAny, List


class Specification(HasTraits):
    defaults = {}
    machines = {}
    inventory = {}

    def get_param(self, machine_name, param_name):
        "str -> str or None"
        machine = self.machines[machine_name]
        pass

    @classmethod
    def from_dict(cls, spec):
        s = cls()
        s.defaults  = spec['defaults']
        s.machines  = spec['machines']
        s.inventory = spec['inventory']
        return s
