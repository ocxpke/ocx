"""Lector mínimo de ficheros S-expression de KiCad (.kicad_pcb).

No depende de KiCad: tokeniza el fichero y devuelve listas anidadas.
Las cadenas entre comillas se devuelven como `str` (sin comillas) y los
átomos sin comillas también como `str`; la conversión a número la hace
quien consume los datos.
"""

import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse(text):
    stack = [[]]
    for m in _TOKEN.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(t[1:-1].encode().decode('unicode_escape') if '\\' in t else t[1:-1])
        else:
            stack[-1].append(t)
    if len(stack) != 1:
        raise ValueError('paréntesis desequilibrados')
    return stack[0][0]


def children(node, name):
    """Hijos directos de `node` cuya cabecera es `name`."""
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == name]


def child(node, name, default=None):
    c = children(node, name)
    return c[0] if c else default


def value(node, name, default=None, idx=1):
    c = child(node, name)
    if c is None or len(c) <= idx:
        return default
    return c[idx]


def floats(node, name):
    c = child(node, name)
    return [float(v) for v in c[1:]] if c else None
