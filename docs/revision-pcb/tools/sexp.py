"""Minimal S-expression parser for KiCad files (no external deps)."""
import re
_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')
def parse(text):
    stack=[[]]; pos=0; n=len(text)
    while pos<n:
        m=_tok.match(text,pos)
        if not m: break
        pos=m.end()
        o,c,s,a=m.groups()
        if o: stack.append([])
        elif c:
            x=stack.pop(); stack[-1].append(x)
        elif s is not None: stack[-1].append(bytes(s[1:-1],'utf-8').decode('unicode_escape') if '\\' in s else s[1:-1])
        elif a is not None: stack[-1].append(a)
    return stack[0][0]
def find(node,key):
    return [c for c in node if isinstance(c,list) and c and c[0]==key]
def first(node,key,default=None):
    r=find(node,key); return r[0] if r else default
def val(node,key,default=None,i=1):
    r=first(node,key); return r[i] if r is not None and len(r)>i else default
