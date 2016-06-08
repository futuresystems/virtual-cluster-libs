
from pyparsing import CaselessLiteral, Literal, Optional, Word,\
    pyparsing_common
import pyparsing
from string import ascii_letters,  digits, letters, punctuation
import copy
import os


################################################################################
## utils
################################################################################

def lowerDirective(tokens):
    """Downcase the `directive` token
    """
    return tokens.directive.lower()


################################################################################
## parser
################################################################################

"""
Expansions are defined as follows:

expansion := start (env | count) end
start := "<<"
delim := ">>"
env := "env" delim env_var_name [delim env_var_value]
env_var_name := alphanumeric | "-" | "_" | "+"

symbol := alpha [alpha | digit | "."]
enumerate := "enumerate" delim symbol_list delim integer
"""

def Directive(literal):
    return \
        CaselessLiteral(literal)\
        .setResultsName('directive')\
        .setParseAction(lowerDirective)


env_var_name_alphabet_init = letters
env_var_name_alphabet_rest = letters + '_'
env_var_vals_alphabet = digits + letters + punctuation + ' \t'
symbol_alphabet = (letters, letters + digits + '_.')



class Parser(object):

    def __init__(self):

        start = Literal('<<')
        end = Literal('>>')
        delim = Literal(':')

        symbol = Word(*symbol_alphabet).setResultsName('symbol')

        env_var_name = Word(env_var_name_alphabet_init,
                            env_var_name_alphabet_rest)\
                            .setResultsName('env')

        env_directive = Directive('env')
        env = env_directive + delim + env_var_name

        index_value = Word(digits)\
                .setResultsName('index')\
                .setParseAction(lambda s, loc, toks: int(toks['index']))

        index = Directive('index') \
                + delim + symbol \
                + Optional(delim + symbol.setResultsName('attribute')) \
                + delim + index_value
        expansion = start + (env ^ index) + end


        inherit = Directive('inherit') + delim + symbol
        forall = Directive('forall') + delim + symbol \
                 + Optional(delim + symbol.setResultsName('attribute'))

        keyword = start + (inherit ^ index ^ forall) + end


        self.start = start
        self.end = end
        self.delim = delim
        self.symbol = symbol
        self.env = env
        self.index = index
        self.expansion = expansion
        self.inherit = inherit
        self.forall = forall
        self.keyword = keyword


    @classmethod
    def transform(cls, parsername, handlers, string):
        P = cls()
        parser = getattr(P, parsername)
        for h in handlers:
            parser.addParseAction(h)
        return parser.transformString(string)


p = Parser()
start = p.start
end = p.end
delim = p.delim
symbol = p.symbol
env = p.env
index = p.index
expansion = p.expansion
inherit = p.inherit
forall = p.forall
keyword = p.keyword


################################################################################
## some handlers
################################################################################

def env_handler(tokens):
    print 'Expanding', tokens.env
    return os.getenv(tokens.env)


################################################################################
## tests
################################################################################

from hypothesis import given, example
from hypothesis.strategies import text, composite, one_of, sampled_from, integers, lists, just, none

from easydict import EasyDict
from functools import partial
import operator

def expected(**kws):
    return EasyDict(kws)

def assertOp(op, left, right):
    assert op(left, right), (left, right)

assertEQ = partial(assertOp, operator.eq)

################################################## strategies


@composite
def symbols(draw):
    start_alpha, rest_alpha = symbol_alphabet

    start = draw(text(start_alpha, min_size=1))
    rest  = draw(text(rest_alpha))
    return start + rest


@composite
def indices(draw): #  I couldn't bring myself to use 'indexes'
    directive = draw(sampled_from('index Index INdex INDex INDEx INDEX'.split()))

    symbol = '.'.join(draw(lists(symbols(), min_size=1)))
    attr   = draw(symbols())

    index = draw(integers(min_value=0))
    r = '{}:{}:{}:{}'.format(directive, symbol, attr, index)
    return r, expected(symbol=symbol, attribute=attr, index=index)


@composite
def envs(draw):
    directive = draw(sampled_from('env ENV eNv EnV eNV ENv'.split()))
    name_start = draw(text(env_var_name_alphabet_init, min_size=1))
    name_rest  = draw(text(env_var_name_alphabet_rest))
    name = name_start + name_rest

    result = '{}:{}'.format(directive, name)
    return result, expected(name=name)


@composite
def expansions(draw):
    elements = one_of(envs(), indices())
    x, es = draw(elements)
    return '<<{}>>'.format(x), es


@composite
def inherits(draw):
    directive = draw(sampled_from('inherit inHERit INHERIT'.split()))
    symbol = draw(symbols())
    s = '{}:{}'.format(directive, symbol)
    return s, expected(directive=directive.lower(), symbol=symbol)


@composite
def foralls(draw):
    directive = draw(sampled_from('forall foRAll FORALL'.split()))
    symbol = draw(symbols())
    attr   = draw(one_of(none(), symbols()))
    s = '{}:{}'.format(directive, symbol)
    if attr:
        s += ':{}'.format(attr)
    return s, expected(directive=directive.lower(), symbol=symbol)


@composite
def keywords(draw):
    k, expected = draw(one_of(inherits(), foralls()))
    return '<<{}>>'.format(k), expected


################################################## tests

@given(one_of(just(':'), just('<<'), just('>>')))
def test_literal(lit):
    p = delim ^ start ^ end
    assert p.parseString(lit)


@given(envs())
def test_env(val):
    s, expected = val
    r = env.parseString(s)
    assert 'env' in r.keys()
    assertEQ(r.env, expected.name)



@given(indices())
@example(('index:foo.bar:42', expected(symbol='foo.bar', index=42)))
def test_index(val):
    s, expected = val
    r = index.parseString(s)
    assert 'index' in r.keys()
    assert 'symbol' in r.keys()

    assertEQ(r.symbol, expected.symbol)
    assertEQ(r.index, expected.index)

    

@given(expansions())
def test_expansion(val):
    s, expected = val
    r = expansion.parseString(s)
    assert 'directive' in r.keys()
    if r.directive == 'env':
        assert 'env' in r.keys()
        assertEQ(r.env, expected.name)
    elif r.directive == 'index':
        assert 'index' in r.keys()
        assert 'symbol' in r.keys()
        assertEQ(r.symbol, expected.symbol)
        assertEQ(r.index, expected.index)
    else:
        raise ValueError('Unknown directive {}'.format(r['directive']))


@given(inherits())
def test_inherit(val):
    s, expected = val
    r = inherit.parseString(s)
    assert 'directive' in r.keys()
    assert 'symbol' in r.keys()
    assertEQ(r.directive, expected.directive)
    assertEQ(r.symbol, expected.symbol)


@given(foralls())
def test_forall(val):
    s, expected = val
    r = forall.parseString(s)
    assert 'directive' in r.keys()
    assert 'symbol' in r.keys()
    assertEQ(r.directive, expected.directive)
    assertEQ(r.symbol, expected.symbol)


@given(keywords())
def test_keywords(val):
    s, expected = val
    assert keyword.parseString(s)



def run_tests():
    test_literal()
    test_env()
    test_index()
    test_expansion()
    test_keywords()


if __name__ == '__main__':
    run_tests()
