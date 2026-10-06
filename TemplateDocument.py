from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from WikiPreprocessor import Parse, Flat, FlatNode, Node, Text, Braces, Warning
from TemplateOutline import Arguments, IsSimple

# The (non-GUI) model behind the template editor.
# The template is held only as text.  Every edit replaces one range of that text and the whole template is then re-parsed,
# so what we show is always exactly what MediaWiki will see, and nothing outside the edited range can change.


# One item in the editor's tree.  Selecting it edits text[start:end].
@dataclass
class Item:
    label: str
    start: int
    end: int
    trimmed: bool       # MediaWiki ignores whitespace at the ends of this range, so we keep the existing whitespace
    children: list[Item]=field(default_factory=list)


def _Preview(s: str, n: int=60) -> str:
    if s and not s.strip():
        s=s.replace(" ", "·")   # Make whitespace-only text visible
    s=s.replace("\n", "⏎")
    return s if len(s) <= n else s[:n-1]+"…"


# Build the tree items for a list of nodes which starts at off in the source.
# Complex constructs get their own item; each run of everything else becomes a single text item.
def _Items(nodes: list[Node], off: int, src: str) -> list[Item]:
    items: list[Item]=[]
    runStart=-1
    pos=off
    for n in nodes+[None]:
        if n is None or (type(n) is Braces and not IsSimple(n)):
            if runStart >= 0:
                items.append(Item(_Preview(src[runStart:pos]), runStart, pos, False))
                runStart=-1
            if n is None:
                break
            items.append(_BracesItem(n, pos, src))
        elif runStart < 0:
            runStart=pos
        pos+=len(FlatNode(n))
    return items


def _BracesItem(b: Braces, off: int, src: str) -> Item:
    end=off+len(FlatNode(b))
    head, args=Arguments(b, off)
    # Label it with its head and a glimpse of its first argument, e.g. "{{#ifeq: {{{start}}}{{{end}}} …}}"
    label=head
    if head.endswith(":") and args:
        label+=" "+_Preview(src[args[0].start:args[0].end], 30)
    if args:
        label+=" …"
    item=Item(label+("}}}" if b.count == 3 else "}}"), off, end, False)
    for arg in args:
        child=Item(arg.label+": "+(_Preview(src[arg.start:arg.end]) or "(empty)"), arg.start, arg.end, arg.trimmed)
        # Only show what's inside a value if it is more than one simple run
        inner=_Items(arg.nodes, arg.start, src)
        if len(inner) > 1 or (len(inner) == 1 and inner[0].children):
            child.children=inner
        item.children.append(child)
    return item


class TemplateDocument:
    def __init__(self, text: str, name: str=""):
        self.name: str=name
        self.original: str=text
        self.history: list[str]=[]
        self.text: str=""
        self.nodes: list[Node]=[]
        self.warnings: list[Warning]=[]
        self.originalWarnings: list[Warning]=Parse(text)[1]
        self._SetText(text)

    def _SetText(self, text: str):
        self.text=text
        self.nodes, self.warnings=Parse(text)
        assert Flat(self.nodes) == text     # The parse is lossless, so this can only fail if the parser is broken

    @property
    def Changed(self) -> bool:
        return self.text != self.original

    def Tree(self) -> list[Item]:
        return _Items(self.nodes, 0, self.text)

    # The text an item's edit box should show
    def ItemText(self, item: Item) -> str:
        return self.text[item.start:item.end]

    # Replace an item's text.  Returns False if nothing changed.
    def Apply(self, item: Item, new: str) -> bool:
        if item.trimmed:
            new=new.strip()     # Whitespace at the ends would be ignored by MediaWiki; don't let it sneak into the source
        text=self.text[:item.start]+new+self.text[item.end:]
        if text == self.text:
            return False
        self.history.append(self.text)
        self._SetText(text)
        return True

    def Undo(self) -> bool:
        if not self.history:
            return False
        self._SetText(self.history.pop())
        return True

    def Diff(self) -> str:
        return "\n".join(difflib.unified_diff(self.original.split("\n"), self.text.split("\n"), "original", "edited", lineterm=""))

    # Brace problems in the template's output (not its <noinclude> documentation) which were not there originally
    def NewWarnings(self) -> list[Warning]:
        before=[w.message for w in self.originalWarnings if not w.inDoc]
        new=[]
        for w in self.warnings:
            if w.inDoc:
                continue
            if w.message in before:
                before.remove(w.message)
            else:
                new.append(w)
        return new
