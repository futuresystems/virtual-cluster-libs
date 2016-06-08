
from pyparsing import CaselessLiteral, Literal, Optional, Word,\
    pyparsing_common
from string import ascii_letters,  digits, letters, punctuation
import copy


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

env_var_name_alphabet_init = letters
env_var_name_alphabet_rest = letters + '_'
env_var_vals_alphabet = digits + letters + punctuation + ' \t'


start = Literal('<<')
end = Literal('>>')
delim = Literal(':')

symbol_alphabet = (letters, letters + digits + '_.')

symbol = Word(*symbol_alphabet).setResultsName('symbol')

env_var_name = Word(env_var_name_alphabet_init,
                    env_var_name_alphabet_rest)\
                    .setResultsName('env')

env_directive = CaselessLiteral('env')\
                .setResultsName('directive')\
                .setParseAction(lambda toks: toks['directive'].lower())
env = env_directive + delim + env_var_name

index_directive = CaselessLiteral('index')\
                  .setResultsName('directive')\
                  .setParseAction(lambda toks: toks['directive'].lower())

index_value = Word(digits)\
        .setResultsName('index')\
        .setParseAction(lambda s, loc, toks: int(toks['index']))
              
index = index_directive + delim + symbol + delim + index_value
expansion = start + (env ^ index) + end

################################################################################
## handlers
################################################################################

def env_handler(token):
    import os
    var = token.env
    return os.getenv(var)


def index_handler(scope, token):
    print 'hello'
    return 'FOOBAR'
    # namespace = token.symbol.split('.')
    # obj = scope
    # for attr in namespace:
    #     obj = getattr(obj, attr)

    # assert isinstance(obj, Sequence)
    # for i, x in enumerate(obj, token.index):
    #     yield i



def transform(parser, actions, string):
    if '<<env:OS_PROJECT_NAME>>-net' in string:
        import pdb; pdb.set_trace()
    
    parser_copy = copy.copy(parser)
    parser_copy.addParseAction(*actions)
    return parser_copy.transformString(string)


################################################################################
## tests
################################################################################

from hypothesis import given, example, assume
from hypothesis.strategies import text, composite, one_of, sampled_from, integers, binary, fractions, decimals, floats, booleans, lists, tuples
from pyparsing import ParseException


class LiteralParserTesters(object):

    def _test(self, literal, parser, example):
        if example.startswith(literal):
            assert parser.parseString(example)
        else: # should throw exception
            try:
                parser.parseString(example)
            except Exception as e:
                assert isinstance(e, ParseException), e
            else:
                raise ValueError(example)

    def run(self):
        self.test_start()
        self.test_end()
        self.test_delim()


    @given(text())
    @example('<<')
    def test_start(self, s):
        assume(len(s.strip()) > 0)
        self._test('<<', start, s)


    @given(text())
    @example('>>')
    def test_end(self, s):
        assume(len(s.strip()) > 0)
        self._test('>>', end, s)


    @given(text())
    @example(':')
    def test_delim(self, s):
        assume(len(s.strip()) > 0)
        self._test(':', delim, s)


@composite
def env_strategy(draw):
    directive = draw(sampled_from('env ENV eNv EnV eNV ENv'.split()))
    name_start = draw(text(env_var_name_alphabet_init, min_size=1))
    name_rest  = draw(text(env_var_name_alphabet_rest))
    name = name_start + name_rest

    result = '{}:{}'.format(directive, name)
    return result, name


@given(env_strategy())
def test_env(val):
    s, expected = val
    r = env.parseString(s)
    assert 'env' in r.keys()
    assert r['env'] == expected, (r['env'], expected)


@composite
def symbols(draw):
    start_alpha, rest_alpha = symbol_alphabet

    start = draw(text(start_alpha, min_size=1))
    rest  = draw(text(rest_alpha))
    return start + rest


@composite
def index_strategy(draw):
    directive = draw(sampled_from('index Index INdex INDex INDEx INDEX'.split()))

    symbol = '.'.join(draw(lists(symbols(), min_size=1)))

    index = draw(integers(min_value=0))
    r = '{}:{}:{}'.format(directive, symbol, index)
    return r, (symbol, index)


@given(index_strategy())
@example(('index:foo.bar:42',('foo.bar',42)))
def test_index(val):
    s, (symbol, ix) = val
    r = index.parseString(s)
    assert 'index' in r.keys()
    assert 'symbol' in r.keys()
    assert r.symbol == symbol, (r.symbol, symbol)
    assert r.index == ix, (r.index, ix)


@composite
def expansion_strategy(draw, elements=one_of(env_strategy(), index_strategy())):
    x, expected = draw(elements)
    return '<<{}>>'.format(x), expected
    

@given(expansion_strategy())
def test_expansion(val):
    s, expected = val
    r = expansion.parseString(s)
    assert 'directive' in r.keys()
    if r['directive'] == 'env':
        assert 'env' in r.keys()
        assert r['env'] == expected
    elif r['directive'] == 'index':
        assert 'index' in r.keys()
        assert 'symbol' in r.keys()
        assert r.symbol == expected[0]
        assert r.index == expected[1]
    else:
        raise ValueError('Unknown directive {}'.format(r['directive']))


@composite
def index_object(draw):
    string, (symbol, value) = draw(index_strategy())

    class dummy(object):
        pass

    fields = symbol.split('.')
    start = dummy()
    obj = start

    for f in fields[:-1]:
        new = dummy()
        setattr(obj, f, new)
        obj = new
    setattr(obj, fields[-1], value)

    return dict(object=start,
                string=string,
                symbol=symbol,
                value=value,)


@given(index_object())
def test_transform(datum):
    object = datum['object']
    string = datum['string']

    from functools import partial
    ih = partial(index_handler, object)

    transform(expansion, [env_handler, ih], string

    

    # scope = datum['object']
    # name = datum['name']
    # value = datum['value']



def run_tests():
    LiteralParserTesters().run()
    test_env()
    test_index()
    test_expansion()


if __name__ == '__main__':
    run_tests()
