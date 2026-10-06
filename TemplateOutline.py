from __future__ import annotations

import os
import sys
import glob
from dataclasses import dataclass

from HelpersPackage import WikiPagenameToWindowsFilename

from WikiPreprocessor import Parse, Flat, Node, Text, Braces, Link, Warning, SplitNamed, SplitFunction, Strip

# Prints an indented outline of a MediaWiki template so its structure can be read.
#   TemplateOutline.py Person [Toolbar ...]     -- outline the named templates from the local site mirror
#   TemplateOutline.py --check                  -- check every template in the mirror: lossless parse + brace warnings
# The outline is for reading only.  Newlines which are part of the template's output are shown as ⏎.

SiteDir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "site")

Step="    "
Inline=60       # Constructs whose source is no longer than this (and simple) are shown on one line

# Labels for the arguments of the parser functions.  The first argument is the one after the colon.
ArgLabels: dict[str, list[str]]={
    "#if": ["test", "then", "else"],
    "#ifeq": ["a", "b", "then", "else"],
    "#iferror": ["test", "if error", "else"],
    "#ifexpr": ["expr", "then", "else"],
    "#ifexist": ["page", "then", "else"],
    "#expr": ["expr"],
}
SwitchFunctions={"#switch", "#switchcategory"}


def IsSimple(n: Node) -> bool:
    s=Flat([n])
    if "\n" in s or len(s) > Inline:
        return False
    if type(n) is Braces:
        # Never hide a parser function inside a line unless it is tiny
        return all(IsSimple(x) for part in n.parts for x in part) and (SplitFunction(n.parts[0]) is None or len(s) <= 30)
    if type(n) is Link:
        return all(IsSimple(x) for part in n.parts for x in part)
    return True


# Outline a list of nodes as a list of lines (without the indent of the caller)
def Outline(nodes: list[Node]) -> list[str]:
    lines: list[str]=[]
    cur=""
    for n in nodes:
        if type(n) is Text:
            segs=n.s.split("\n")
            for seg in segs[:-1]:
                lines.append(cur+seg+"⏎")
                cur=""
            cur+=segs[-1]
            continue
        if IsSimple(n):
            cur+=Flat([n])
            continue
        if cur.strip():
            lines.append(cur)
        cur=""
        if type(n) is Braces:
            lines.extend(OutlineBraces(n))
        else:
            lines.extend(Flat([n]).split("\n"))
    if cur.strip():
        lines.append(cur)
    return lines


# Outline one labeled argument: on the label's line if it fits, else indented below it
def OutlineArg(label: str, nodes: list[Node], width: int) -> list[str]:
    body=Outline(nodes) if nodes else ["(empty)"]
    if len(body) == 1:
        return [Step+label.ljust(width)+": "+body[0]]
    return [Step+label.ljust(width)+":"]+[Step*2+x for x in body]


def OutlineBraces(b: Braces) -> list[str]:
    # {{{parameter|default}}}
    if b.count == 3:
        lines=["{{{"+Flat(b.parts[0])+"|"]
        for part in b.parts[1:]:
            lines.extend([Step+x for x in Outline(part)])
        return lines+["}}}"]

    head, args=Arguments(b)
    width=max([len(x.label) for x in args], default=0)
    lines=[head]
    for arg in args:
        lines.extend(OutlineArg(arg.label, arg.nodes, width))
    return lines+["}}"]


# One argument of a {{template}} or {{#function:}}, or the default of a {{{parameter}}}
@dataclass
class Arg:
    label: str
    nodes: list[Node]   # The value (trimmed if MediaWiki trims it)
    start: int          # Where the value is in the source -- relative to the offset passed to Arguments()
    end: int
    trimmed: bool       # MediaWiki ignores whitespace at the ends of this value


# Return the trimmed form of a value which starts at off, and the range it occupies in the source
def _Trimmed(nodes: list[Node], off: int) -> tuple[list[Node], int, int]:
    s=Flat(nodes)
    if not s.strip():
        return [], off, off     # All whitespace: an empty range in front of it
    return Strip(nodes), off+len(s)-len(s.lstrip()), off+len(s.rstrip())


# Return the head (e.g. "{{#ifeq:") and the labeled arguments of a Braces node which starts at off in the source
def Arguments(b: Braces, off: int=0) -> tuple[str, list[Arg]]:
    # Offsets of each |-separated part
    partOffs: list[int]=[]
    pos=off+b.count
    for part in b.parts:
        partOffs.append(pos)
        pos+=len(Flat(part))+1

    def Whole(label: str, part: list[Node], poff: int) -> Arg:
        nodes, start, end=_Trimmed(part, poff)
        return Arg(label, nodes, start, end, True)

    def Named(label: str, kv: tuple[list[Node], list[Node]], poff: int, prefix: str="") -> Arg:
        nodes, start, end=_Trimmed(kv[1], poff+len(Flat(kv[0]))+1)
        return Arg(prefix+Flat(Strip(kv[0])), nodes, start, end, True)

    args: list[Arg]=[]

    # {{{parameter|default}}} -- the default is not trimmed
    if b.count == 3:
        for j, part in enumerate(b.parts[1:], 1):
            args.append(Arg("default", part, partOffs[j], partOffs[j]+len(Flat(part)), False))
        return "{{{"+Flat(b.parts[0]).strip(), args

    func=SplitFunction(b.parts[0])
    if func is not None:
        name, first=func
        head="{{"+name+":"
        rest=[first]+b.parts[1:]
        restOffs=[partOffs[0]+len(b.parts[0][0].s.split(":", 1)[0])+1]+partOffs[1:]
        if name.lower() in SwitchFunctions:
            # #switch's first argument is the value being switched on; #switchcategory tests the page's categories, so all of its arguments are cases
            if name.lower() == "#switch":
                args.append(Whole("value", rest[0], restOffs[0]))
                rest=rest[1:]
                restOffs=restOffs[1:]
            for part, poff in zip(rest, restOffs):
                kv=SplitNamed(part)
                if kv is None:
                    args.append(Whole("default", part, poff))
                else:
                    args.append(Named("", kv, poff, "case "))
        else:
            labels=ArgLabels.get(name.lower(), [])
            for j, (part, poff) in enumerate(zip(rest, restOffs)):
                args.append(Whole(labels[j] if j < len(labels) else f"arg {j+1}", part, poff))
        return head, args

    head="{{"+Flat(b.parts[0]).strip()
    pos=0
    for part, poff in zip(b.parts[1:], partOffs[1:]):
        kv=SplitNamed(part)
        if kv is None:
            pos+=1
            args.append(Arg(str(pos), part, poff, poff+len(Flat(part)), False))   # Positional parameters are NOT trimmed by MediaWiki
        else:
            args.append(Named("", kv, poff))
    return head, args


def LineOf(s: str, offset: int) -> int:
    return s.count("\n", 0, offset)+1


def TemplateFile(name: str) -> str:
    return os.path.join(SiteDir, WikiPagenameToWindowsFilename("Template:"+name)+".txt")


def ShowTemplate(name: str):
    with open(TemplateFile(name), encoding="utf-8") as fd:
        s=fd.read()
    nodes, warnings=Parse(s)
    print(f"===== Template:{name} =====")
    if Flat(nodes) != s:
        print("*** The parse is not lossless -- do not trust this outline ***")
    for w in warnings:
        print(f"*** Line {LineOf(s, w.offset)}: {w.message}"+(" (in <noinclude> documentation)" if w.inDoc else ""))
    for line in Outline(nodes):
        print(line)
    print()


def CheckAll():
    files=sorted(glob.glob(os.path.join(SiteDir, "Template;colon;*.txt")))
    lossy=0
    for f in files:
        with open(f, encoding="utf-8") as fd:
            s=fd.read()
        nodes, warnings=Parse(s)
        if Flat(nodes) != s:
            lossy+=1
            print(f"NOT LOSSLESS: {os.path.basename(f)}")
        for w in warnings:
            print(f"{os.path.basename(f)} line {LineOf(s, w.offset)}: {w.message}"+(" (in <noinclude> documentation)" if w.inDoc else ""))
    print(f"{len(files)} templates checked, {lossy} not lossless")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        CheckAll()
    else:
        for arg in sys.argv[1:]:
            ShowTemplate(arg)
