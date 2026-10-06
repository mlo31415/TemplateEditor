from __future__ import annotations

import os
import sys

import wx

from TemplateOutline import Outline, TemplateFile, LineOf
from TemplateDocument import TemplateDocument, Item
from WikiPreprocessor import Parse

# A GUI editor for MediaWiki templates.
# The left side is a tree of the template's structure.  Selecting an item shows its outline and puts its source in the edit box.
# Apply replaces exactly that source and re-parses the whole template; the Changes pane shows the diff against the original
# and any brace problems the edit introduced.  The result is saved to a file or copied to the clipboard for pasting into the wiki.


class TemplateEditorFrame(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent, title="Template Editor", size=wx.Size(1400, 900))
        self.doc: TemplateDocument|None=None
        self.item: Item|None=None           # The item being edited
        self.path: list[int]|None=None      # Its path in the tree
        self.exported: str=""               # The text last saved or copied
        self.rebuilding: bool=False         # Ignore tree selection events while the tree is being rebuilt

        mono=wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        panel=wx.Panel(self)

        # Buttons
        buttons=wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("Open Template...", self.OnOpenTemplate), ("Open File...", self.OnOpenFile), ("Save As...", self.OnSaveAs),
                               ("Copy to Clipboard", self.OnCopy), ("Undo", self.OnUndo)]:
            b=wx.Button(panel, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            buttons.Add(b, 0, wx.ALL, 4)

        splitter=wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE)

        # Left: the structure tree
        self.tree=wx.TreeCtrl(splitter, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT)
        self.tree.SetFont(mono)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGING, self.OnSelChanging)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged)

        # Right: outline, edit box, changes
        right=wx.Panel(splitter)
        rs=wx.BoxSizer(wx.VERTICAL)
        rs.Add(wx.StaticText(right, label="Outline of the selection"), 0, wx.LEFT | wx.TOP, 4)
        self.outline=wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.outline.SetFont(mono)
        rs.Add(self.outline, 3, wx.EXPAND | wx.ALL, 4)

        self.editLabel=wx.StaticText(right, label="Source of the selection")
        rs.Add(self.editLabel, 0, wx.LEFT, 4)
        self.edit=wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.HSCROLL)
        self.edit.SetFont(mono)
        rs.Add(self.edit, 2, wx.EXPAND | wx.ALL, 4)
        eb=wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in [("Apply", self.OnApply), ("Revert", self.OnRevert)]:
            b=wx.Button(right, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            eb.Add(b, 0, wx.ALL, 4)
        rs.Add(eb, 0)

        self.status=wx.StaticText(right, label="")
        rs.Add(self.status, 0, wx.LEFT, 4)
        self.diff=wx.TextCtrl(right, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.diff.SetFont(mono)
        rs.Add(self.diff, 2, wx.EXPAND | wx.ALL, 4)
        right.SetSizer(rs)

        splitter.SplitVertically(self.tree, right, 520)
        splitter.SetMinimumPaneSize(200)

        ms=wx.BoxSizer(wx.VERTICAL)
        ms.Add(buttons, 0)
        ms.Add(splitter, 1, wx.EXPAND)
        panel.SetSizer(ms)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Show()


    #------------------------------------------------------------------
    def Load(self, text: str, name: str):
        self.doc=TemplateDocument(text, name)
        self.exported=text
        self.item=None
        self.SetTitle(f"Template Editor -- {name}")
        self.RebuildTree(keepExpanded=False)

    # OK to throw away the current document?
    def OkToDiscard(self) -> bool:
        if self.doc is None or self.doc.text == self.exported:
            return True
        return wx.MessageBox("The edited template has not been saved or copied.  Discard the changes?", "Template Editor", wx.YES_NO | wx.NO_DEFAULT, self) == wx.YES

    #------------------------------------------------------------------
    # The tree is rebuilt after every change.  Items are identified by their path (list of child indexes) so that the
    # selection and the expanded items can be restored.
    def RebuildTree(self, selPath: list[int]|None=None, keepExpanded: bool=True):
        expanded=self.ExpandedPaths(self.tree.GetRootItem(), []) if keepExpanded and self.tree.GetRootItem().IsOk() else None
        self.item=None
        self.rebuilding=True
        self.tree.Freeze()
        self.tree.DeleteAllItems()
        root=self.tree.AddRoot("")
        self.AddItems(root, self.doc.Tree(), [], expanded)
        self.tree.Thaw()
        self.rebuilding=False

        if selPath is not None:
            ti=self.ItemAtPath(selPath)
            if ti is not None:
                self.tree.SelectItem(ti)
                self.tree.EnsureVisible(ti)
        if self.item is None:
            self.ShowItem(None)
        self.ShowChanges()

    def AddItems(self, parent: wx.TreeItemId, items: list[Item], path: list[int], expanded: set[tuple]|None):
        for i, item in enumerate(items):
            ti=self.tree.AppendItem(parent, item.label)
            self.tree.SetItemData(ti, (item, path+[i]))
            self.AddItems(ti, item.children, path+[i], expanded)
            # By default expand just the top level
            if item.children and ((expanded is None and not path) or (expanded is not None and tuple(path+[i]) in expanded)):
                self.tree.Expand(ti)

    def ExpandedPaths(self, ti: wx.TreeItemId, path: list[int]) -> set[tuple]:
        out: set[tuple]=set()
        child, cookie=self.tree.GetFirstChild(ti)
        i=0
        while child.IsOk():
            if self.tree.IsExpanded(child):
                out.add(tuple(path+[i]))
            out|=self.ExpandedPaths(child, path+[i])
            child, cookie=self.tree.GetNextChild(ti, cookie)
            i+=1
        return out

    def ItemAtPath(self, path: list[int]) -> wx.TreeItemId|None:
        ti=self.tree.GetRootItem()
        for i in path:
            child, cookie=self.tree.GetFirstChild(ti)
            for _ in range(i):
                if not child.IsOk():
                    break
                child, cookie=self.tree.GetNextChild(ti, cookie)
            if not child.IsOk():
                return None
            ti=child
        return ti

    #------------------------------------------------------------------
    def EditPending(self) -> bool:
        return self.item is not None and self.edit.GetValue() != self.doc.ItemText(self.item)

    def OnSelChanging(self, event):
        if self.rebuilding or not self.EditPending():
            return
        r=wx.MessageBox("Apply the change you made in the edit box?", "Template Editor", wx.YES_NO | wx.CANCEL, self)
        if r == wx.CANCEL:
            event.Veto()
        elif r == wx.YES:
            # Applying rebuilds the tree, so veto this selection and make it again in the new tree
            event.Veto()
            target=self.tree.GetItemData(event.GetItem())[1] if event.GetItem().IsOk() else self.path
            if self.doc.Apply(self.item, self.edit.GetValue()):
                self.RebuildTree(target)
            else:
                # The edit made no difference to the template (e.g., only whitespace MediaWiki ignores), so just move on
                self.OnRevert(None)
                self.tree.SelectItem(event.GetItem())

    def OnSelChanged(self, event):
        if self.rebuilding:
            return
        ti=event.GetItem()
        data=self.tree.GetItemData(ti) if ti.IsOk() else None
        self.ShowItem(data)

    def ShowItem(self, data: tuple[Item, list[int]]|None):
        if data is None:
            self.item=None
            self.path=None
            self.outline.SetValue("")
            self.edit.ChangeValue("")
            self.editLabel.SetLabel("Source of the selection")
            return
        self.item, self.path=data
        src=self.doc.ItemText(self.item)
        self.outline.SetValue("\n".join(Outline(Parse(src)[0])))
        self.edit.ChangeValue(src)
        if self.item.trimmed:
            self.editLabel.SetLabel("Source of the selection  (MediaWiki ignores whitespace at the ends of this value)")
        else:
            self.editLabel.SetLabel("Source of the selection  (whitespace and newlines here are part of the output)")

    def ShowChanges(self):
        diff=self.doc.Diff()
        self.diff.SetValue(diff if diff else "(no changes)")
        new=self.doc.NewWarnings()
        if new:
            self.status.SetForegroundColour(wx.RED)
            self.status.SetLabel("NEW BRACE PROBLEMS: "+"; ".join([f"line {LineOf(self.doc.text, w.offset)}: {w.message}" for w in new]))
        else:
            self.status.SetForegroundColour(wx.BLACK)
            self.status.SetLabel("Changes from the original" if self.doc.Changed else "No changes")
        self.status.GetParent().Layout()

    #------------------------------------------------------------------
    def OnApply(self, event):
        if self.item is None:
            return
        path=self.path
        if self.doc.Apply(self.item, self.edit.GetValue()):
            self.RebuildTree(path)
        else:
            self.ShowItem((self.item, self.path))

    def OnRevert(self, event):
        if self.item is not None:
            self.edit.ChangeValue(self.doc.ItemText(self.item))

    def OnUndo(self, event):
        if self.doc is not None and self.doc.Undo():
            self.RebuildTree(self.path)

    #------------------------------------------------------------------
    def OnOpenTemplate(self, event):
        if not self.OkToDiscard():
            return
        dlg=wx.TextEntryDialog(self, "Template name (without 'Template:')", "Open Template")
        if dlg.ShowModal() == wx.ID_OK:
            self.OpenTemplate(dlg.GetValue().strip())
        dlg.Destroy()

    def OpenTemplate(self, name: str):
        fname=TemplateFile(name)
        if not os.path.exists(fname):
            wx.MessageBox(f"There is no Template:{name} in the site mirror\n({fname})", "Template Editor", wx.OK, self)
            return
        with open(fname, encoding="utf-8") as fd:
            self.Load(fd.read(), "Template:"+name)

    def OnOpenFile(self, event):
        if not self.OkToDiscard():
            return
        dlg=wx.FileDialog(self, "Open template source", wildcard="Text files (*.txt)|*.txt|All files|*.*", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            with open(dlg.GetPath(), encoding="utf-8") as fd:
                self.Load(fd.read(), dlg.GetPath())
        dlg.Destroy()

    # Before the text leaves the editor, make sure the user knows about any new brace problems
    def OkToExport(self) -> bool:
        if self.doc is None:
            return False
        if self.EditPending():
            if wx.MessageBox("The edit box has a change which has not been applied.  Continue without it?", "Template Editor", wx.YES_NO | wx.NO_DEFAULT, self) != wx.YES:
                return False
        if self.doc.NewWarnings():
            return wx.MessageBox("Your edits have introduced brace problems (see the red message).  Continue anyway?", "Template Editor", wx.YES_NO | wx.NO_DEFAULT, self) == wx.YES
        return True

    def OnSaveAs(self, event):
        if not self.OkToExport():
            return
        default=self.doc.name.replace(":", "_")+".txt"
        dlg=wx.FileDialog(self, "Save template source", defaultFile=default, wildcard="Text files (*.txt)|*.txt", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            with open(dlg.GetPath(), "w", encoding="utf-8", newline="\n") as fd:
                fd.write(self.doc.text)
            self.exported=self.doc.text
        dlg.Destroy()

    def OnCopy(self, event):
        if not self.OkToExport():
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.doc.text))
            wx.TheClipboard.Close()
            self.exported=self.doc.text

    def OnClose(self, event):
        if event.CanVeto() and not self.OkToDiscard():
            event.Veto()
            return
        event.Skip()


def main():
    app=wx.App(False)
    frame=TemplateEditorFrame(None)
    name=sys.argv[1] if len(sys.argv) > 1 else "Person"
    frame.OpenTemplate(name)
    app.MainLoop()


if __name__ == "__main__":
    main()
