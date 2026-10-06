from __future__ import annotations

import re
from dataclasses import dataclass, field

# A parser for MediaWiki template source which follows the rules of MediaWiki's own preprocessor (Preprocessor_Hash).
# The preprocessor is the stage which decides what is a {{template}}, a {{{parameter}}} and a | separator, so following its
# rules means we see the same structure MediaWiki sees -- including when a mistake in the braces makes MediaWiki see something
# other than what the author intended.
#
# The parse is lossless: Flat(Parse(s)) == s for every s.

# Extension tags whose contents the preprocessor does not look inside
OpaqueTags={"nowiki", "pre", "ref", "references", "gallery", "math", "syntaxhighlight", "source", "poem", "templatedata", "score", "timeline"}
# Tags which control transclusion.  Their contents are parsed normally.
MarkerTags={"noinclude", "includeonly", "onlyinclude"}


#==================================================================================
# The nodes of the parse tree
@dataclass
class Text:
    s: str

@dataclass
class Comment:
    s: str      # Including the <!-- -->

@dataclass
class RawTag:
    s: str      # An opaque tag, including its contents and the closing tag

@dataclass
class Marker:
    s: str      # <noinclude>, </includeonly>, etc.

@dataclass
class Braces:
    count: int                  # 2 for {{template}}, 3 for {{{parameter}}}
    parts: list[list[Node]]     # The |-separated parts.  parts[0] is the name.
    offset: int=0               # Where in the source it starts

@dataclass
class Link:
    parts: list[list[Node]]     # [[a|b]] -- kept as a node only so that its | and = are not taken as the enclosing template's

Node=Text|Comment|RawTag|Marker|Braces|Link


@dataclass
class Warning:
    offset: int
    message: str
    inDoc: bool=False   # It is inside <noinclude>, which is never part of the template's output


def Flat(nodes: list[Node]) -> str:
    return "".join([FlatNode(x) for x in nodes])

def FlatNode(n: Node) -> str:
    if type(n) is Braces:
        return "{"*n.count+"|".join([Flat(p) for p in n.parts])+"}"*n.count
    if type(n) is Link:
        return "[["+"|".join([Flat(p) for p in n.parts])+"]]"
    return n.s


#==================================================================================
# An unclosed {{, {{{ or [[ on the parse stack
@dataclass
class _Piece:
    open: str           # "{" or "["
    count: int          # Number of opening characters still unmatched
    offset: int
    parts: list[list[Node]]=field(default_factory=lambda: [[]])


def _Append(accum: list[Node], n: Node):
    # Merge adjacent Text nodes so that the tree stays tidy
    if type(n) is Text:
        if not n.s:
            return
        if accum and type(accum[-1]) is Text:
            accum[-1]=Text(accum[-1].s+n.s)
            return
    accum.append(n)


# Parse template source into a list of nodes.  Problems with the braces are reported in warnings.
def Parse(s: str) -> tuple[list[Node], list[Warning]]:
    root: list[Node]=[]
    stack: list[_Piece]=[]
    warnings: list[Warning]=[]

    def Accum() -> list[Node]:
        return stack[-1].parts[-1] if stack else root

    i=0
    while i < len(s):
        c=s[i]

        # Comments are opaque
        if s.startswith("<!--", i):
            end=s.find("-->", i+4)
            end=len(s) if end == -1 else end+3
            _Append(Accum(), Comment(s[i:end]))
            i=end
            continue

        # Tags
        if c == "<":
            m=re.match(r"<(/?)([a-zA-Z]+)(\s[^>]*)?(/?)>", s[i:])
            if m is not None:
                name=m.group(2).lower()
                if name in MarkerTags:
                    _Append(Accum(), Marker(m.group(0)))
                    i+=len(m.group(0))
                    continue
                if name in OpaqueTags and not m.group(1):
                    if m.group(4):     # <nowiki/>
                        _Append(Accum(), RawTag(m.group(0)))
                        i+=len(m.group(0))
                        continue
                    close=re.compile(r"</"+name+r"\s*>", re.IGNORECASE).search(s, i+len(m.group(0)))
                    if close is not None:
                        _Append(Accum(), RawTag(s[i:close.end()]))
                        i=close.end()
                        continue
            _Append(Accum(), Text(c))
            i+=1
            continue

        # Opening braces or brackets
        if c == "{" or c == "[":
            run=len(s)-i-len(s[i:].lstrip(c))
            if run >= 2:
                stack.append(_Piece(c, run, i))
            else:
                _Append(Accum(), Text(c))
            i+=run
            continue

        # Closing braces or brackets.  They only mean something if they close the piece on top of the stack.
        if stack and ((c == "}" and stack[-1].open == "{") or (c == "]" and stack[-1].open == "[")):
            piece=stack[-1]
            run=len(s)-i-len(s[i:].lstrip(c))
            run=min(run, piece.count)
            if run < 2:
                _Append(Accum(), Text(c))
                i+=1
                continue

            # Braces match 3 ({{{parameter}}}) or 2 ({{template}}); brackets match only 2
            matching=min(run, 3 if c == "}" else 2)
            stack.pop()
            if c == "}":
                node=Braces(matching, piece.parts, piece.offset+piece.count-matching)
            else:
                node=Link(piece.parts)

            # Any opening characters left over either form a new piece or (if only one is left) become plain text
            remaining=piece.count-matching
            if remaining >= 2:
                stack.append(_Piece(piece.open, remaining, piece.offset))
            elif remaining == 1:
                _Append(Accum(), Text(piece.open))
                warnings.append(Warning(piece.offset, f"'{piece.open*piece.count}' was closed by only {matching} -- the extra '{piece.open}' is plain text"))
            _Append(Accum(), node)
            i+=matching
            continue

        # A | starts a new part of the current piece
        if c == "|" and stack:
            stack[-1].parts.append([])
            i+=1
            continue

        # Any other character is just text.  Grab the whole run of uninteresting characters at once.
        m=re.compile(r"[^<{}\[\]|]+").match(s, i)
        if m is not None and m.end() > i:
            _Append(Accum(), Text(m.group(0)))
            i=m.end()
        else:
            # A stray }} which closes nothing
            if c == "}" and s.startswith(c*2, i):
                warnings.append(Warning(i, f"'{c*2}' closes nothing -- it is plain text"))
                _Append(Accum(), Text(c*2))
                i+=2
                continue
            _Append(Accum(), Text(c))
            i+=1

    # Anything still open at the end is plain text
    while stack:
        piece=stack.pop()
        if piece.open == "{":
            warnings.append(Warning(piece.offset, f"'{piece.open*piece.count}' is never closed -- it is plain text"))
        _Append(Accum(), Text(piece.open*piece.count))
        for j, part in enumerate(piece.parts):
            if j > 0:
                _Append(Accum(), Text("|"))
            for n in part:
                _Append(Accum(), n)

    for m in re.finditer(r"<noinclude>.*?(</noinclude>|$)", s, re.IGNORECASE | re.DOTALL):
        for w in warnings:
            if m.start() <= w.offset < m.end():
                w.inDoc=True
    warnings.sort(key=lambda w: w.offset)
    return root, warnings


#==================================================================================
# Helpers for interpreting a Braces node

# If a part contains a top-level '=', return (key, value) as node lists; otherwise None
def SplitNamed(part: list[Node]) -> tuple[list[Node], list[Node]]|None:
    for j, n in enumerate(part):
        if type(n) is Text and "=" in n.s:
            k=n.s.index("=")
            return part[:j]+[Text(n.s[:k])], [Text(n.s[k+1:])]+part[j+1:]
    return None


# For {{name:arg|...}} return (name, first arg) if it is a parser function like #if or a magic word like lc:
# Otherwise None
def SplitFunction(part: list[Node]) -> tuple[str, list[Node]]|None:
    if not part or type(part[0]) is not Text or ":" not in part[0].s:
        return None
    name, rest=part[0].s.split(":", 1)
    if not re.fullmatch(r"\s*#?[a-zA-Z]+\s*", name):
        return None
    return name.strip(), [Text(rest)]+part[1:]


# Strip leading and trailing whitespace from a node list (MediaWiki does this to named parameters and parser function arguments)
def Strip(nodes: list[Node]) -> list[Node]:
    nodes=list(nodes)
    if nodes and type(nodes[0]) is Text:
        nodes[0]=Text(nodes[0].s.lstrip())
    if nodes and type(nodes[-1]) is Text:
        nodes[-1]=Text(nodes[-1].s.rstrip())
    return [x for x in nodes if not (type(x) is Text and not x.s)]
