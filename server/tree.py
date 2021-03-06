"""
merge 2 dict
Examples:

>>> merge({'ip1': {'cpu': 0.2}}, {'ip1': {'cpu': 0.4}})
{'ip1': {'cpu': [0.2, 0.4]}}

>>> merge({'ip1': {'cpu': 0.2}}, a=3,b=3)
{'a': 3, 'ip1': {'cpu': 0.2}, 'b': 3}

>>> merge({'ip1': {'cpu': 0.2}}, {'ip1': {'net': 10}})
{'ip1': {'net': 10, 'cpu': 0.2}}

query dict by pattern
Examples:

>>> d = {'ip1': { 'cpu': 0.2, 'net':120 },
...     'ip2': { 'cpu': 0.3, 'net':10 },
...     'ip3': { 'cpu0': 0.3, 'cpu1':0.6 },
...     'arr': [0.3,0.6],
...     }
>>> type(d)
<type 'dict'>

>>> list(query(d, 'ip1,net'))
[(['ip1', 'net'], 120)]

>>> for i in query(d, 'ip*,cpu'): print i
(['ip2', 'cpu'], 0.3)
(['ip1', 'cpu'], 0.2)

>>> for i in query(d, 'ip*,cpu*'): print i
(['ip2', 'cpu'], 0.3)
(['ip3', 'cpu0'], 0.3)
(['ip3', 'cpu1'], 0.6)
(['ip1', 'cpu'], 0.2)

>>> for i in query(d, 'ip*|list,cpu*|avg'): print i
(['ip2', 'cpu*'], 0.3)
(['ip3', 'cpu*'], 0.45)
(['ip1', 'cpu*'], 0.2)

>>> for i in query(d, '*|sum,net'): print i
(['*'], 130.0)

>>> for i in query(d, '*|avg,net'): print i
(['*'], 65.0)

>>> for i in query(d, 'ip*|avg,cpu*|avg'): print i
(['ip*'], 0.31666666666666665)
"""

import copy
import operator
import fnmatch
import math, decimal

def keyin(key, d):
    arr = key.split(',')
    for a in arr:
        if a in d:
            d = d[a]
        else:
            return False
    return True

def _loop_by(d1, d2):
    assert isinstance(d2, dict)
    for k,v2 in d2.iteritems():
        if not isinstance(v2, dict):
            yield (k in d1), d1, d2, k, v2
        else:
            v1 = d1.get(k)

            if v1 is None:
                yield False, d1, d2, k, v2
                continue
            
            for t in _loop_by(v1, v2):
                yield t

def merge(d, *args, **kwargs):
    """ merge 2 dict, return the first
    """
    if len(kwargs) ==0 and len(args) and isinstance(args[0], dict):
        kwargs = args[0]
    for keyin, d1,d2,key,v2 in _loop_by(d, kwargs):
        if keyin:
            v1 = d1[key]
            if not isinstance(v1, list):
                v1 = [v1]
            assert isinstance(v2, (int, float)), (key,v2,d2)
            v1.append(v2)
            d1[key] = v1
        else:
            d1[key] = copy.deepcopy(v2)
    return d

def add(d, *args, **kwargs):
    """ TODO: code same as merge
    """
    if len(kwargs) ==0 and len(args) and isinstance(args[0], dict):
        kwargs = args[0]
    for keyin, d1,d2,key,v2 in _loop_by(d, kwargs):
        if keyin:
            v1 = d1[key]
            assert isinstance(v2, (int, float)), (key,v2)
            assert isinstance(v1, (int, float)), (key,v1)
            v1 += v2
            d1[key] = v1
        else:
            d1[key] = copy.deepcopy(v2)
    return d

def match(s, pat):
    return fnmatch.fnmatchcase(s, pat)

def expand(d, keys=None, sep=','):
    """iterator all dict item, recursively

    >>> list(expand({'a':2}))
    [('a', 2)]
    >>> list(expand({'1':2},['a']))
    [('a,1', 2)]
    >>> list(expand({'1':2, '2':{'3':5}},['a']))
    [('a,1', 2), ('a,2,3', 5)]
    """
    if keys is None:
        keys = []

    if not isinstance(d, dict):
        yield sep.join(keys), d
    else:
        for k,v in d.iteritems():
            keys.append(k)
            for t in expand(v, keys, sep):
                yield t
            keys.pop()
        
def loop(d):
    """recursively iterate item of dict"""
    assert isinstance(d, dict)
    for k,v in d.iteritems():
        if not isinstance(v, dict):
            yield [k], v
        else:
            for t in loop(v):
                ks = [k]
                ks.extend(t[0])
                yield ks, t[1]

def proc_by_name(name, iter):
    return sum(iter)

def _avg(iter):
    a = sum(iter)
    c = decimal.Decimal(str(a)) / len(iter)
    return float(c)

def _query(d, pats):
    if isinstance(pats, str):  pats = [pats]
    if not isinstance(pats, (list, tuple)): 
        assert False, ('unexpected type', type(pats))
        
    last_i = len(pats) - 1

    if not isinstance(d, dict):
        return

    sub_dict = d
    for i, (pat, action) in enumerate(pats):
        if '*' in pat or '?' in pat:
            ret = []
            def gather(t1, t2): 
                ret.append((t1,t2))
            for k,v in sub_dict.iteritems():
                if match(k, pat):
                    if last_i == i and not isinstance(v, dict):
                        # yield [k], v
                        gather([k], v)
                    for t in _query(v, pats[i+1:]):
                        ks = [k]
                        ks.extend(t[0])
                        # yield ks, t[1]
                        gather(ks, t[1])
            if ret:
                if action is not None and action != 'list':
                    get1 = operator.itemgetter(1)
                    try:
                        a = math.fsum(map(get1, ret))
                    except:
                        assert False, (action, ret)

                    if action == 'avg':
                        #print 'avg:', ret, a, '/', len(ret)
                        a = decimal.Decimal(str(a)) / len(ret)
                        a = float(a)
                    yield [pat], a
                else:
                    for t in ret:
                        yield t
        else:
            sub_dict = sub_dict.get(pat)
            if sub_dict is None: return

            if not isinstance(sub_dict, dict):
                yield [pat], sub_dict
                return
            else:
                if last_i == i:
                    y = loop(sub_dict)
                else:
                    y = _query(sub_dict, pats[i+1:])

                for t in y:
                    ks = [pat]
                    ks.extend(t[0])
                    yield ks, t[1]
        return

def query(d, s):
    assert isinstance(d, dict), (type(d),d)
    pat_action_list = []
    for i in s.split(','):
        if '|' in i:
            pat, action = i.split('|')
        else:
            pat, action = i, None
        pat_action_list.append((pat, action))

    for t in _query(d, pat_action_list):
        yield t

if __name__ == '__main__':
    import pprint
    d = {'ip1': { 'cpu': 0.2, 'net':120 }, \
         'ip2': { 'cpu': 0.3, 'net':10 }, \
         'ip3': { 'cpu0': 0.3, 'cpu1':0.6 }, \
         'foo': 3, \
         'arr': [10,9,8], \
         'a' : {'b' : {'c' : {'d':42}}} \
        }
    pprint.pprint(d)
    print 'loop(d)'
    for i in loop(d): print i

    cases = [
             '*,net',
             '*|sum,net',
             'ip1,cpu',
             'ip2,cpu',
             'ip1,net',
             'ip1',
             'a',
             'ip*,cpu',
             '*1,net*',
             '?p?,net*',
             'ip*,net*',
             'ip*,cpu*',
             'ip*|list,cpu*|avg',
        ]

    for c in cases:
        print c, ' ' * 4, list(query(d, c))

    assert 7 == proc_by_name('', [1,2,4])    
    assert 0.45 == _avg([0.3,0.6])
