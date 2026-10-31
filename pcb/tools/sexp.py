"""Reads and writes KiCad's S-expression files.

A list is a Python list; a quoted string is a Q; anything else is a str atom.
"""
import re


class Q(str):
    """A quoted string."""


TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack, out = [], None
    for m in TOKEN.finditer(text):
        if m.group(1):
            stack.append([])
        elif m.group(2):
            done = stack.pop()
            if stack:
                stack[-1].append(done)
            else:
                out = done
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        else:
            stack[-1].append(m.group(4))
    return out


def atom(x):
    if isinstance(x, Q):
        return '"' + x.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(x, float):
        return f"{x:.4f}".rstrip("0").rstrip(".") or "0"
    return str(x)


def dump(x, indent=0):
    """Writes x in KiCad's layout, keeping every element in its order: a list of atoms
    stays on one line, and otherwise each element after the leading atoms gets a line."""
    if not isinstance(x, list):
        return atom(x)
    if all(not isinstance(i, list) for i in x):
        return "(" + " ".join(atom(i) for i in x) + ")"
    lead = 0
    while lead < len(x) and not isinstance(x[lead], list):
        lead += 1
    lines = ["(" + " ".join(atom(i) for i in x[:lead])]
    for i in x[lead:]:
        lines.append("\t" * (indent + 1) + dump(i, indent + 1))
    lines.append("\t" * indent + ")")
    return "\n".join(lines)


def find(x, key):
    """The first child list whose head is key."""
    return next((i for i in x if isinstance(i, list) and i and i[0] == key), None)


def find_all(x, key):
    return [i for i in x if isinstance(i, list) and i and i[0] == key]
