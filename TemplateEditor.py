from __future__ import annotations
from dataclasses import dataclass
from abc import abstractmethod

import wx
from wx import richtext as rtc
import enum

from Log import Log

from GenTemplateEditor import MyFrame1

class TemplateEditorFrame(MyFrame1):
    def __init__(self, parent):
        MyFrame1.__init__(self, parent)
        self.nodes: Node=Node("")

        self.Show()


    def OnTextTop( self, event ):
        s=self.m_TopText.GetValue()
        root=Node(s)
        root.type=NodeType.Root
        self.nodes=root.Process()
        Log("\n*********************\nNodes")
        Log(repr(self.nodes))
        #s=parseTemplate(s)
        r=RichTextSpec(self.m_richText1, 0)
        r.rtc.Clear()
        self.nodes.RichText(r)


    def OnTextBottom(self, event):
        s=self.m_BottomText.GetValue()
        #s=unparseTemplate(s)
        #self.m_TopText2.ChangeValue(s)


@dataclass
class RichTextSpec:
    rtc: rtc
    indent: int
    
#===================
@dataclass
class Delim:
    _loc: int
    delim: str

    def __str__(self) -> str:
        return self.delim

    @property
    def IsOpen(self) -> bool:
        return self.delim == "{{" or self.delim == "{{{"

    @property
    def End(self) -> int:
        return self._loc+len(self.delim)

    @property
    def Start(self) -> int:
        return self._loc

    @property
    def Len(self) -> int:
        return len(self.delim)

    @property
    def NotFound(self) -> bool:
        return self._loc == -1

    def Matching(self, val: Delim) -> bool:
        return self.Len == val.Len and self.delim != val.delim

    # -----------------------------------------------------------
    @staticmethod
    # Find the next delimiter in s beginning at start
    def Nextdelim(s: str, start: int, Open: bool = False, Close: bool = False) -> Delim:
        if Open:
            delims=["{{{", "{{"]  # Note that these are searched in order and thus must be sorted longest to shortest
        elif Close:
            delims=["}}}", "}}"]
        else:
            delims=["{{{", "}}}", "{{", "}}"]
        loc=-1
        delim=""
        for d in delims:
            l=s[start:].find(d)
            if l == -1:
                continue    # Failed to find delimiter d
            if loc == -1 or loc > l:
                loc=l   # We found a delimiter which is the closest found so far
                delim=d
        # OK, at this point loc and delim records the next delim...or none at all
        de=Delim(start+loc, delim)
        sprime=s+" "
        Log(f"Nextdelim: s[start:]='{s[start:]}'  Delim={de}  Remainder='{sprime[de.End:]}'")
        return de


##################################################################################
class NodeType(enum.Enum):
    Empty=0
    String=1    # Contains a string, but no Nodes
    Double=2    # {{}} plus contents as a list of Nodes
    Triple=3    # {{{}}} plus contents as a list of Nodes
    Nodes=4     #
    Root=5      # The root of the template: A list of subnodes only.  There is only one Root

    def __str__(self) -> str:
        if self == NodeType.Empty:
            return "Empty"
        if self == NodeType.String:
            return "String"
        if self == NodeType.Double:
            return "Double"
        if self == NodeType.Triple:
            return "Triple"
        if self == NodeType.Root:
            return "Root"




##################################################################################
# Holds a node in the tree of embedded {{}} and {{{}}} expressions in a template
# A Node can be empty or hold a string or a series of Nodes, optionally inside a {{}} or {{{}}}
# A String Node can contain a string
class Node():
    offset: int=0  # Offset used by __repr__
    zcount: int=0       # The z is to move these to the end of the variable lists while debugging
    znodelist: list[Node]=[]

    def __init__(self, s: str):
        self.subnodes: list[Node]=[]       # A list of subnodes for this node
        self.type: NodeType=NodeType.Empty  # Normally overwritten
        self.string=s

        # We track the Nodes using this universal ID and list
        self.id=Node.zcount
        Node.zcount+=1  # Ready for the next one
        Node.znodelist.append(self)
        Log(f"Node #{self.id} ('{self.string}', {self.type}) created.")


    def __str__(self) ->str:
        if self.type == NodeType.Empty:
            return ""

        # A Node can either have subnodes or a string  (maybe?)
        if self.subnodes:
            nstr="".join([str(x) for x in self.subnodes])
        else:
            nstr=self.string
        return nstr



    def __repr__(self) -> str:
        Log(f"repr #{self.id}")
        offset=" "*Node.offset  # For this call to repr, we use the offset at start
        if self.type == NodeType.Empty:
            return offset+f"Node #{self.id} -- {self.type}"

        if self.type == NodeType.Root:
            Node.offset+=3
            r=offset+f"Node #{self.id} -- {self.type},  subnodes:\n"+"".join([repr(x)+"\n" for x in self.subnodes])
            Node.offset-=3
            return r




    def RichText(self, r: RichTextSpec) -> None:
        if self.type == NodeType.Empty:
            return

        indent=' '*r.indent
        if self.type == NodeType.Root:
            r.rtc.WriteText("Root\n")
            if self.subnodes:
                r.indent+=2
                for x in self.subnodes:
                    x.RichText(r)
                r.indent-=2
            return

        assert False


    @abstractmethod
    def WriteNodes(self, indent: str, r: rtc):
        pass


    #-----------------------------------------------------
    # Find the first open delim
    def FindFirstOpenDelim(self) -> Delim:
        d0=Delim.Nextdelim(self.string, 0, Open=True)
        if d0.NotFound:
            if self.type == NodeType.String:
                return Delim(-1, "")  # There's no further processing possible here

            # Turn the text into a String sub-node
            self.subnodes.append(NodeString(self.string))
            Log(f"FindFirstOpenDelim: Node #{self.subnodes[-1].id} appended to Node #{self.id}")
            self.string=""
            return Delim(-1, "")

        return d0

    #--------------------------------------------------------
    # Extract the next useful piece of this Node
    def Nibble(self) -> tuple[Delim, Delim]:

        d0=self.FindFirstOpenDelim()
        if d0.NotFound:
            return d0, d0

        # OK, do is the beginning delimiter. Scan the remainder of the string looking for the matching delimiter at depth zero.
        stack: list[Delim]=[d0]  # Push d0 onto the stack
        s=self.string
        loc=d0.End  # loc marks the end of the just-found delimiter
        while True:
            # Find the next delimiter (open or closed)
            d=Delim.Nextdelim(s, loc)
            loc=d.End
            if d.IsOpen:
                # If this is an open delim, add it to the stack and continue looking
                stack.append(d)
                continue

            # Then it must be a close delimiter.  In a properly constructed template, the matching open delim must be at the top of the stack.
            # First make sure the stak has something in it!
            if not stack:
                Log(f"*** Nibble: Process error: stack is empty")
                return Delim(-1, ""), Delim(-1, "")

            # Since d is a closing delimiter, the stack top should hold the matching opening delimiter.
            dt=stack.pop()
            if not d.Matching(dt):
                Log(f"*** Nibble: Process error: {d=} and {dt=} don't match")
                return Delim(-1, ""), Delim(-1, "")

            # We know that we have found a closing delimiter that matches the open delim.
            # If the stack is non-empty, then we have found an internal delimiter pair, but not yet the closing delimiter.
            # So we keep going.
            if stack:
                continue

            # The stack is empty and we have found a closing delimiter.
            # (I.e., all the intervening start-end delim pairs have been found and cancelled out.)
            # If it matches the opening delimiter, d0, then we're done.
            if not d0.Matching(d):
                Log(f"*** Nibble: Process error: empty stack, no match -- {d0.Len=} != {d.Len=}")
                return Delim(-1, ""), Delim(-1, "")

            return d0, d

    # Take a node and recursively break it up into subnodes
    # If it is a String, Double or Triple node, we examine it and if it contains subnodes, we replace it with a Nodes, Double or Triple(a list of Nodes)
    # The we
    def Process(self) -> Node:
        assert not self.subnodes
        Log(f"Processing Node #{self.id}")

        Log("")

        d0, d=self.Nibble()
        if d0.NotFound:
            return self

        # We have found a matching set of delimiters.  The string we analyzed is now broken into parts:
        # 0 -- l0-1   -- Opening string
        # l0 -- l0+len(d0)-1      -- the delimiter
        # l0+len(d0) -- lt-1      -- the contents of the node
        # lt -- lt+len(dt)-1   -- the closing delimiter
        # lt+len(dt) -- end    -- trailing string

        # We will recursively recognize each of the new subnodes as we create them.
        s=self.string
        lead=s[:d0.Start]       # The text before d0
        mid=s[d0.End:d.Start]   # The text between d0 and d
        end=s[d.End:]           # The text after d
        Log(f"Process: {lead=}  {mid=}  {end=}")

        # Sometimes we have a String node which, when processed turns out to have subnodes.  We need to change the parent appropriately.
        # ?? Allow a string node to have subnodes?
        # ?? Create a nodetype which is nothing but subnodes?
        # Since this situation occurs when we have "string {{triple}}" we *probably* want to delete the string and a new string and triple to the parent's nodelist

        # The node we're processing, as yet, has no subnodes
        # We can zero out the string since we are processing it into the nodelist
        if lead or mid or end:
            self.string=""
            if self.type == NodeType.String and self.subnodes:
                # Reach up and change self
                pass

        # Turn each of the parts into a new Node on the current Node's subnodes list
        if lead:
            self.subnodes.append(NodeString(lead).Process())
            Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")
        if mid:
            if d0.Len == 2:
                self.subnodes.append(NodeDouble(mid).Process())
                Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")
            elif d0.Len == 3:
                self.subnodes.append(NodeTriple(mid).Process())
                Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")

        if end:
            self.subnodes.append(NodeString(end).Process())
            Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")

        return self


class NodeContainer(Node):
    def __init__(self, s: str):
        super().__init__(s)

    def __repr__(self) -> str:
        r=""
        offset=" "*Node.offset
        if self.string:
            r=offset+f"Node #{self.id} -- {self.type},  '{self.string}'"
        if self.subnodes:
            Node.offset+=3
            r+=offset+f"Node #{self.id} -- {self.type},  subnodes:\n"+"".join([repr(x)+"\n" for x in self.subnodes])
            Node.offset-=3
        return r

    def RichText(self, r: RichTextSpec):
        Log(f"Node(#{self.id},  {self.type}, subnodes={len(self.subnodes)}, '{self.string}'")
        # Special case it when the Node has a single string node inside
        indent=' '*r.indent
        if self.string:
            r.rtc.WriteText(indent+self.string+"\n")
        elif len(self.subnodes) == 1 and self.subnodes[0].type == NodeType.String and self.subnodes[0].string:
            r.rtc.WriteText(indent+self.subnodes[0].string+"\n")
        if self.subnodes:
            self.WriteNodes(indent, r)


    def WriteGenericNodes(self, indent: str, r: rtc, bopen: str, bclose: str):
        r.rtc.WriteText(indent+bopen)
        r.indent+=2
        for x in self.subnodes:
            x.RichText(r)
        r.indent-=2
        r.rtc.WriteText(indent+bclose)

#-------------------------------------------
class NodeString(NodeContainer):

    def __init__(self, s: str) -> None:
        super().__init__(s)
        self.type=NodeType.String
        self.string: str=""

    def WriteNodes(self, indent: str, r: rtc):
        super().WriteGenericNodes(indent, r, "", "")

#-------------------------------------------
class NodeDouble(NodeContainer):
    def __init__(self, s: str) -> None:
        super().__init__(s)
        self.type=NodeType.Double

    def __str__(self) -> str:
        s=super().__str__()
        return "{{"+s+"}}"

    def WriteNodes(self, indent: str, r: rtc):
        super().WriteGenericNodes(indent, r, "{{\n", "}}\n")

#-------------------------------------------
class NodeTriple(NodeContainer):
    def __init__(self, s: str) -> None:
        super().__init__(s)
        self.type=NodeType.Triple

    def __str__(self) -> str:
        s=super().__str__()
        return "{{{"+s+"}}}"

    def WriteNodes(self, indent: str, r: rtc):
        super().WriteGenericNodes(indent, r, "{{{\n", "}}}\n")



def main():
    app=wx.App(False)
    frame=TemplateEditorFrame(None)

    app.MainLoop()
    Log("Exit mainloop")



if __name__ == "__main__":
    main()