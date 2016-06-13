import vcl.logger as logging
logger = logging.getLogger(__name__)

from parser import Parser

import copy
import operator

import traits.api as T
from traits.api import HasTraits



class Visitor(HasTraits):

    handlers = T.List()
    context  = T.Any()


    def _getSymbolBy(self, getter, instance, symbol):
        names = symbol.split('.')
        i = instance
        for name in names:
            if not name: break
            i = getter(i, name)
        return i

    def _getObjectSymbol(self, obj, symbol):
        return self._getSymbolBy(getattr, obj, symbol)


    def _getDictSymbol(self, dictionary, symbol):
        return self._getSymbolBy(operator.getitem, dictionary, symbol)


    def _getSymbol(self, value, symbol):
        if isinstance(value, dict):
            return self._getDictSymbol(value, symbol)
        else:
            return self._getObjectSymbol(value, symbol)


    def transform(self, spec):
        self.spec = copy.deepcopy(spec)
        return self.visit(self.spec)


    def visit_generic(self, node):
        return node


    def visit(self, node):
        typ  = type(node).__name__
        attr = 'visit_{}'.format(typ)
        visitor = getattr(self, attr, self.visit_generic)
        logger.debug('Visiting type={} method={}'.format(typ, visitor.func_name))
        logger.debug('Value="{}"'.format(repr(node)))
        return visitor(node)


    def transform_dict(self, node, key):


        logger.debug('Transforming dict key: {}'.format(key))

        ### don't use pyparsing's addParseAction as this causes
        ### bizarre errors (likely due to some pyparsing
        ### statefullness)


        p = Parser()
        parsed = p.keyword.parseString(key)
        logger.debug('Parsed items: {}'.format(parsed.items()))
        
        if parsed.directive == 'inherit':
            # This replaces the <<inherits:...>> keyword with the target.

            spec = self._getDictSymbol(self.spec, parsed.symbol)
            spec = copy.copy(spec)
            del node[key]
            for k, v in node.iteritems():
                spec[k] = v

            for k, v in spec.iteritems():
                node[k] = v


        elif parsed.directive == 'index':
            seq = self._getObjectSymbol(self.context, parsed.symbol)

            for variable in node[key].keys():
                for i, val in enumerate(seq, parsed.index):
                    k = self._getSymbol(val, parsed.attribute)
                    if k not in node:
                        node[k] = dict()
                    node[k][variable] = i
            del node[key]


        elif parsed.directive == 'forall':
            seq = self._getObjectSymbol(self.context, parsed.symbol)

            for variable, value in node[key].iteritems():
                for val in seq:
                    k = self._getSymbol(val, parsed.attribute)
                    if k not in node:
                        node[k] = dict()
                    node[k][variable] = value
            del node[key]

        else:
            logger.error('Unable to handle directive "{}"'.format(parsed.directive))
            raise ValueError("I don't know how to handle directive {}"
                             .format(parsed.directive))


    def visit_dict(self, node):

        seen = set()

        logger.debug('Visiting dict keys')
        while True:
            keys = set(node.keys())

            try:
                k = keys.difference(seen).pop()
            except KeyError:
                break

            logger.debug('Processing key "{}"'.format(k))
            if k.startswith('<<') and k.endswith('>>'):
                self.transform_dict(node, k)
            seen.add(k)


        logger.debug('Visiting dict values')
        for k in node:
            logger.add()
            node[k] = self.visit(node[k])
            logger.sub()

        return node


    def visit_list(self, node):
        for i in xrange(len(node)):
            logger.add()
            node[i] = self.visit(node[i])
            logger.sub()
        return node


    def visit_str(self, node):
        return Parser.transform('expansion', self.handlers, node)

