from __future__ import annotations

import os
import glob

from TemplateOutline import SiteDir
from TemplateDocument import TemplateDocument, Item

# Tests for TemplateDocument, run against every template in the local site mirror:
#   1. Writing each item's own text back leaves the template unchanged (so every item's range is right)
#   2. Every trimmed item's range has no whitespace at its ends
#   3. A real edit changes only the edited range, and Undo restores the original
#   4. Breaking a brace is reported as a new warning


def AllItems(items: list[Item]) -> list[Item]:
    out=[]
    for x in items:
        out.append(x)
        out.extend(AllItems(x.children))
    return out


def Main():
    files=sorted(glob.glob(os.path.join(SiteDir, "Template;colon;*.txt")))
    count=0
    for f in files:
        with open(f, encoding="utf-8") as fd:
            s=fd.read()
        doc=TemplateDocument(s)
        for item in AllItems(doc.Tree()):
            t=doc.ItemText(item)
            assert not doc.Apply(item, t), f"{f}: writing back '{item.label}' changed the template"
            if item.trimmed:
                assert t == t.strip(), f"{f}: trimmed item '{item.label}' has whitespace at its ends"
            count+=1
    print(f"Test 1+2: {len(files)} templates, {count} items written back unchanged")

    with open(os.path.join(SiteDir, "Template;colon;t^^oolbar.txt"), encoding="utf-8") as fd:
        s=fd.read()
    doc=TemplateDocument(s)
    items=AllItems(doc.Tree())
    target=[x for x in items if x.label.startswith("else: [[{{{end}}}]]")][0]
    assert doc.Apply(target, "  [[{{{end}}}]] (died)  ")
    assert doc.text == s.replace("|||[[{{{end}}}]]}}", "|||[[{{{end}}}]] (died)}}"), doc.text
    assert doc.Changed and not doc.NewWarnings()
    assert doc.Undo() and doc.text == s and not doc.Changed
    print("Test 3: edit of a nested #ifeq branch changed only that branch; Undo restored it")

    target=[x for x in AllItems(doc.Tree()) if x.label.startswith("a: {{{start}}}{{{end}}}")][0]
    doc.Apply(target, "{{{start}}{{{end}}}")
    assert len(doc.NewWarnings()) == 1, doc.NewWarnings()
    print("Test 4: a dropped brace is reported:", doc.NewWarnings()[0].message)
    print("All tests passed")


if __name__ == "__main__":
    Main()
