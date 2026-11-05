"""Minimal S-expression reader/writer for KiCad files."""
import re

TOKEN = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    pos = 0
    stack = [[]]
    n = len(text)
    while pos < n:
        m = TOKEN.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError(f'parse error at {pos}: {text[pos:pos+40]!r}')
        pos = m.end()
        lp, rp, s, a = m.groups()
        if lp:
            stack.append([])
        elif rp:
            node = stack.pop()
            stack[-1].append(node)
        elif s is not None:
            stack[-1].append(re.sub(r'\\(.)', lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), s[1:-1]))
        elif a is not None:
            stack[-1].append(Sym(a))
    return stack[0][0] if len(stack[0]) == 1 else stack[0]


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def dump(node, indent=0):
    """Serialise a parsed tree back to text (strings quoted, Syms bare)."""
    if isinstance(node, list):
        if not node:
            return '()'
        simple = all(not isinstance(x, list) for x in node)
        head = dump(node[0])
        if simple:
            return '(' + ' '.join(dump(x) for x in node) + ')'
        parts = [head]
        out = '(' + head
        for x in node[1:]:
            if isinstance(x, list):
                out += '\n' + '\t' * (indent + 1) + dump(x, indent + 1)
            else:
                out += ' ' + dump(x)
        return out + '\n' + '\t' * indent + ')'
    if isinstance(node, Sym):
        return str(node)
    if isinstance(node, (int, float)):
        return fmt(node)
    return q(node)


def fmt(v):
    if isinstance(v, int):
        return str(v)
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def find(node, key):
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def find_all(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def load_lib(path):
    with open(path, encoding='utf-8') as f:
        tree = parse(f.read())
    return {x[1]: x for x in find_all(tree, 'symbol')}


def flatten(lib, name):
    """Return a copy of symbol `name` with any (extends ...) resolved."""
    import copy
    sym = copy.deepcopy(lib[name])
    ext = find(sym, 'extends')
    if not ext:
        return sym
    base = flatten(lib, ext[1])
    # properties of the derived symbol override the base ones
    props = {p[1]: p for p in find_all(sym, 'property')}
    out = [Sym('symbol'), name]
    for x in base[2:]:
        if isinstance(x, list) and x[0] == 'property' and x[1] in props:
            out.append(props.pop(x[1]))
        elif isinstance(x, list) and x[0] == 'symbol':
            sub = copy.deepcopy(x)
            sub[1] = sub[1].replace(ext[1], name, 1)
            out.append(sub)
        else:
            out.append(x)
    out.extend(props.values())
    return out


def pins(sym):
    """List of (number, name, x, y, angle, length, type) for unit 1 / common."""
    res = []
    for sub in find_all(sym, 'symbol'):
        for p in find_all(sub, 'pin'):
            at = find(p, 'at')
            ln = find(p, 'length')
            name = find(p, 'name')[1]
            num = find(p, 'number')[1]
            res.append((num, name, float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0,
                        float(ln[1]) if ln else 2.54, str(p[1])))
    return res
