from __future__ import annotations
from typing import Optional

import wx
import re as Regex
import enum

from Log import Log

from GenTemplateEditor import MyFrame1

class TemplateEditorFrame(MyFrame1):
    def __init__(self, parent):
        MyFrame1.__init__(self, parent)

        self.Show()

    def OnTextTop( self, event ):
        s=self.m_TopText.GetValue()
        m=MacroTree(s)
        #s=parseTemplate(s)
        self.m_BottomText.ChangeValue(s)

    def OnTextBottom(self, event):
        s=self.m_BottomText.GetValue()
        s=unparseTemplate(s)
        self.m_TopText.ChangeValue(s)


class NodeType(enum.Enum):
    Empty=0
    String=1
    Double=2
    Triple=3


class Node():
    def __init__(self, s: str, nodetype: NodeType):
        self.nodes: list[Node]=[]
        self.string: str=s
        self.type: NodeType=nodetype


    def __str__(self) ->str:
        if self.type == NodeType.Empty:
            return ""
        if self.type == NodeType.String:
            return self.string
        return "".join([str(x) for x in self.nodes])


class MacroTree():
    def __init__(self, s: str):
        self.root: Node=Node(s, NodeType.String)

        if not s:
            return

        nodelist=[]
        ordinarychars="[^{}]"
        triple="({{{)(.*+)(}}})"
        double="({{)(.*+)(}})"
        splits=Regex.split(triple, s)
        if len(splits) > 1:
            # We should have a list of tokens: str {{{ str }}} str
            innode=False
            nodecontent=""
            for split in splits:
                if not split:
                    continue
                if split == "{{{":
                    assert not innode
                    innode=True
                elif split == "}}}":
                    assert innode
                    innode=False
                    node=Node(nodecontent, NodeType.Triple)
                    nodecontent=""
                    self.root.nodes.append(node)
                else:
                    if innode:
                        nodecontent=split
                    else:
                        node=Node(split, NodeType.String)
                        nodelist.append(node)

        if nodelist:
            self.root=nodelist

def parseTemplate(s: str) -> str:
    ordinarychars="[^{}]"       #"[a-zA-Z0-9\s<>\[]=\|]"
    triple="{{{("+ordinarychars+"+?)}}}"
    double="{{("+ordinarychars+"+)}}"
    while s != (s1:=Regex.sub(triple, r"<\1>", s)):
        s=s1
    while s != (s1:=Regex.sub(double, r"[\1]", s)):
        s=s1
    while s != (s1:=Regex.sub(triple, r"<\1>", s)):
        s=s1
    while s != (s1:=Regex.sub(double, r"[\1]", s)):
        s=s1
    return s

def unparseTemplate(s: str) -> str:
    ordinarychars="[^<>[]]"
    double="\[("+ordinarychars+"+?)]"
    triple="<("+ordinarychars+"+?)>"
    while s != (s1:=Regex.sub(double, r"[\1]", s)):
        s=s1
    while s != (s1:=Regex.sub(triple, r"<\1>", s)):
        s=s1
    while s != (s1:=Regex.sub(double, r"[\1]", s)):
        s=s1
    while s != (s1:=Regex.sub(triple, r"<\1>", s)):
        s=s1

    return s


def main():
    app=wx.App(False)
    frame=TemplateEditorFrame(None)

    app.MainLoop()
    Log("Exit mainloop")



if __name__ == "__main__":
    main()