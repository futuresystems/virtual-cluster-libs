
from pyparsing import CaselessLiteral, Literal, Optional, Word
from string import digits, letters, punctuation


"""
Expansions are defined as follows:

expansion := start (env | count) end
start := "<<"
delim := ">>"
env := "env" delim env_var_name [delim env_var_value]
env_var_name := alphanumeric | "-" | "_" | "+"
index := "index" delim integer
"""

env_var_name_alphabet_init = letters
env_var_name_alphabet_rest = letters + '_'
env_var_vals_alphabet = digits + letters + punctuation + ' \t'


start = Literal('<<')
end = Literal('>>')
delim = Literal(':')


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
              
index = index_directive + delim + index_value
expansion = start + (env ^ index) + end

################################################################################
## tests
################################################################################

from hypothesis import given, example, assume
from hypothesis.strategies import text, composite, one_of, sampled_from, integers
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
def index_strategy(draw):
    directive = draw(sampled_from('index Index INdex INDex INDEx INDEX'.split()))
    index = draw(integers(min_value=0))
    r = '{}:{}'.format(directive, index)
    return r, index


@given(index_strategy())
def test_index(val):
    s, expected = val
    r = index.parseString(s)
    assert 'index' in r.keys()
    assert r['index'] == expected, (r['index'], expected)


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
        assert r['index'] == expected
    else:
        raise ValueError('Unknown directive {}'.format(r['directive']))


        

def run_tests():
    LiteralParserTesters().run()
    test_env()
    test_index()
    test_expansion()


if __name__ == '__main__':
    run_tests()
