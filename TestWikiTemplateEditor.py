from __future__ import annotations

import wx

import WikiTemplateEditor
from WikiTemplateEditor import TemplateEditorFrame

# A smoke test of the editor GUI: drive the real frame from code on Template:Toolbar.
# Every dialog is stubbed so nothing pops up; the stub records what was asked and gives a canned answer.

asked: list[str]=[]
answer=wx.YES

def FakeMessageBox(message, caption="", style=0, parent=None):
    asked.append(message)
    return answer


def Run(frame: TemplateEditorFrame):
    global answer
    frame.OpenTemplate("Toolbar")
    original=frame.doc.text

    # Find the 'else: [[{{{end}}}]]' branch by walking the tree
    def Find(ti, prefix):
        child, cookie=frame.tree.GetFirstChild(ti)
        while child.IsOk():
            if frame.tree.GetItemText(child).startswith(prefix):
                return child
            found=Find(child, prefix)
            if found is not None:
                return found
            child, cookie=frame.tree.GetNextChild(ti, cookie)
        return None

    ti=Find(frame.tree.GetRootItem(), "else: [[{{{end}}}]]")
    assert ti is not None
    frame.tree.SelectItem(ti)
    assert frame.edit.GetValue() == "[[{{{end}}}]]", frame.edit.GetValue()
    assert "ignores whitespace" in frame.editLabel.GetLabel()

    # Edit and apply: only that branch changes, the tree is rebuilt and the selection is kept
    frame.edit.SetValue("[[{{{end}}}]] (died)")
    frame.OnApply(None)
    assert frame.doc.text == original.replace("|||[[{{{end}}}]]}}", "|||[[{{{end}}}]] (died)}}")
    assert frame.edit.GetValue() == "[[{{{end}}}]] (died)", frame.edit.GetValue()
    assert "+" in frame.diff.GetValue() and "(died)" in frame.diff.GetValue()
    print("Apply: OK  (selection kept, diff shown)")

    # Moving away with an unapplied edit asks; answering Yes applies it and lands on the item clicked
    frame.edit.SetValue("[[{{{end}}}]] (d.)")
    asked.clear()
    answer=wx.YES
    target=Find(frame.tree.GetRootItem(), "else: [[{{{start}}}]]")
    frame.tree.SelectItem(target)
    assert asked and "Apply" in asked[0]
    assert "(d.)" in frame.doc.text
    assert frame.edit.GetValue() == "[[{{{start}}}]]", frame.edit.GetValue()
    print("Unapplied edit on selection change: asked, applied, moved on: OK")

    # Undo twice gets back to the original
    frame.OnUndo(None)
    frame.OnUndo(None)
    assert frame.doc.text == original and not frame.doc.Changed
    assert frame.diff.GetValue() == "(no changes)"
    print("Undo: OK")

    # A broken brace shows the red warning, and Copy asks before exporting it
    ti=Find(frame.tree.GetRootItem(), "a: {{{start}}}{{{end}}}")
    frame.tree.SelectItem(ti)
    frame.edit.SetValue("{{{start}}{{{end}}}")
    frame.OnApply(None)
    assert frame.status.GetLabel().startswith("NEW BRACE PROBLEMS"), frame.status.GetLabel()
    asked.clear()
    answer=wx.NO
    frame.OnCopy(None)
    assert asked and "brace problems" in asked[0]
    assert frame.exported == original      # Nothing was copied
    print("Brace warning + export check: OK")

    # Closing with unexported changes asks first
    asked.clear()
    answer=wx.YES
    frame.Close()
    assert asked and "Discard" in asked[0]
    print("All GUI tests passed")


def main():
    WikiTemplateEditor.wx.MessageBox=FakeMessageBox
    app=wx.App(False)
    frame=TemplateEditorFrame(None)
    def SafeRun():
        try:
            Run(frame)
        except Exception:
            import traceback
            traceback.print_exc()
            frame.Destroy()     # Don't leave a window hanging on the screen
    wx.CallAfter(SafeRun)
    app.MainLoop()


if __name__ == "__main__":
    main()
