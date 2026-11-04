"""Lector mínimo de S-expressions de KiCad (solo lectura, sin dependencias).

Devuelve listas anidadas: ["footprint", "Lib:Name", ["layer", "F.Cu"], ...].
Las cadenas entre comillas se devuelven como str sin comillas; los átomos
también como str (convertir a float donde haga falta).
"""
import re

_TOKEN = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def parse(text):
    stack = [[]]
    for m in _TOKEN.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(bytes(t[1:-1], "utf-8").decode("unicode_escape")
                             if "\\" in t else t[1:-1])
        else:
            stack[-1].append(t)
    return stack[0][0]


def children(node, name):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == name]


def child(node, name):
    for c in node[1:]:
        if isinstance(c, list) and c and c[0] == name:
            return c
    return None


def prop(node, name):
    for c in children(node, "property"):
        if c[1] == name:
            return c[2]
    return None


def has_flag(node, name):
    """True si existe (name yes) o el átomo suelto 'name' (formatos antiguos)."""
    c = child(node, name)
    if c is not None:
        return len(c) < 2 or c[1] in ("yes", "true")
    return name in node[1:]
