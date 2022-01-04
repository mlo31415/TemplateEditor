from __future__ import annotations
from typing import Union

import re
from dataclasses import dataclass
from abc import abstractmethod

import wx
from wx import TextCtrl
import enum

from Log import Log

from GenTemplateEditor import MyFrame1

class TemplateEditorFrame(MyFrame1):
    def __init__(self, parent):
        MyFrame1.__init__(self, parent)
        self.nodes: Node=Node("", NodeType.Empty)
        self.tokens: Tokens=Tokens()

        self.Show()


    def OnTextTop( self, event ):
        s=self.m_TopText.GetValue().strip()
        root=Node(s, NodeType.Root)
        self.nodes=root.Process()

        b=TextSpec(self.m_bottomText, 0)
        b.TextCtl.Clear()
        self.nodes.PlainText(b)

        Log("\n*********  Nodes  ************")
        Log(repr(self.nodes))

        self.tokens: Tokens=Tokens(s)
        self.tokens.Analyze()
        self.tokens.Compress()
        b2=TextSpec(self.m_bottomText2, 0)
        b2.TextCtl.Clear()
        self.tokens.PlainText(b2)
        #b2.TextCtl.AppendText(str(self.tokens))



    def OnBottomText(self, event):
        s=self.m_bottomText.GetValue()

        # Take the formatted template text and recompact it.
        # Remove the leading "Root:"
        s=s.removeprefix("Root\n")
        # Remove all leading and trailing whitespace from the lines in the (edited) bottom text.
        # That whitespace is was added to make it vaguely readable
        bottom=""
        for line in [x.strip() for x in s.split("\n")]:
            if line:
                if line[0] == "'" and line[-1] == "'":
                    line=line[1:-1]
                bottom+=line
        s="".join(bottom)
        self.m_TopText.ChangeValue(s)

    def OnBottomText2(self, event):
        pass


@dataclass
class TextSpec:
    TextCtl: TextCtl
    indent: int

    def Write(self, s:str):
        self.TextCtl.AppendText(" "*self.indent+s)

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
    def Nextdelim(s: str, start: int, Open: bool = False, Match: str="") -> Delim:
        assert not (Match and Open)
        if Open:
            delims=["{{{", "{{"]  # Note that these are searched in order and thus must be sorted longest to shortest
        elif Match == "{{{":
            delims="}}}"
        elif Match == "{{":
            delims="}}"
        else:
            # Default case
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
        sprime=s#+" "
        Log(f"Nextdelim: s[start:]='{s[start:]}'  Delim={de}  Remainder='{sprime[de.End:]}'")
        return de


##################################################################################
class NodeType(enum.Enum):
    Empty=0
    String=1    # Contains a string, but no Nodes
    Double=2    # {{}} plus contents as a list of Nodes
    Triple=3    # {{{}}} plus contents as a list of Nodes
    Root=4      # The root of the template: A list of subnodes only.  There is only one Root

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

    def __init__(self, s: str, nt: NodeType):
        self.subnodes: list[Node]=[]       # A list of subnodes for this node
        self.type: NodeType=nt
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
        Log(f"repr(1) #{self.id}")

        offset=" "*Node.offset  # For this call to repr, we use the offset at start
        if self.type == NodeType.Empty:
            return offset+f"Node #{self.id} -- {self.type}".rstrip()

        if self.type == NodeType.Root:
            Node.offset+=5
            r=offset+f"Node #{self.id} -- {self.type}\n"+"".join([y+"\n" for y in [repr(x) for x in self.subnodes] if y])
            Node.offset-=5
            return r.rstrip()


    def PlainText(self, r: TextSpec) -> None:
        if self.type == NodeType.Empty:
            return

        if self.type == NodeType.Root:
            r.TextCtl.AppendText("Root\n")
            if self.subnodes:
                r.indent+=5
                for x in self.subnodes:
                    x.PlainText(r)
                r.indent-=5
            return

        assert False

    @abstractmethod
    def WriteNodes(self, r: TextSpec):
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
            # We do greedy parsing, so "}}}}}" will by default be interpreted as "}}}"+"}}"
            # But if the open delimiter is "{{" and the close is "}}}", then either:
            #       We actually have at least "}}}}" (two double closes in a row)
            # or    We have a template syntax error of some sort
            dt=stack.pop()
            if not d.Matching(dt):
                if d.Len < dt.Len:
                    # Maybe greedy parsing got us in trouble. E.g. "{{{{{" being interpreted as {{{+{{ and the matching close being interpreted as }}}+}}
                    # Revert and see if a shorter delimiter is also present. (It usually will be.)
                    loc-=d.Len
                    # We know that we had {{{, so we must have {{
                    d.delim="}}"
                    loc=d.End
                else:
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
    def Process(self) -> Node:
        #assert not self.subnodes
        Log(f"Processing Node #{self.id}")

        #Log("")

        while True:
            d0, d=self.Nibble()
            if d0.NotFound:
                return self

            # We have found a matching set of delimiters.  The string we analyzed is now broken into parts:
            # 0 -- l0-1   -- Opening string
            # l0 -- l0+len(d0)-1      -- the delimiter
            # l0+len(d0) -- lt-1      -- the contents of the node
            # lt -- lt+len(dt)-1   -- the closing delimiter
            # lt+len(dt) -- end    -- trailing string

            @dataclass
            class Parsed:
                lead: str=""
                mid: str=""
                last: str=""

                @property
                def Num(self) -> int:
                    return sum([0 if x == "" else 1 for x in [self.lead, self.mid, self.last]])

            # We will recursively recognize each of the new subnodes as we create them.
            s=self.string
            lead=s[:d0.Start]       # The text before d0 (which does not contain subnodes)
            mid=s[d0.End:d.Start]   # The text between d0 and d (which is a subnode)
            end=s[d.End:]           # The text after d (which may contain subnodes)
            p=Parsed(lead, mid, end)
            Log(f"Process: {lead=}  {mid=}  {end=}")
            self.string=""      # No longer needed

            # Sometimes we have a String node which, when processed turns out to have subnodes.  We need to change the parent appropriately.
            # ?? Allow a string node to have subnodes?
            # ?? Create a nodetype which is nothing but subnodes?
            # Since this situation occurs when we have "string {{triple}}" we *probably* want to delete the string and a new string and triple to the parent's nodelist

            # The node we're processing, as yet, has no subnodes
            # We can zero out the string since we are processing it into the nodelist
            #   lead goes into the subnodes list as a String node.  It needs no further processing.
            #   mid gets processed and then goes into the subnodes list as whetever kind of node it is.
            #   end gets processed and then goes into the subnodes list as whetever kind of node it is.
            if lead:
                self.subnodes.append(NodeString(lead))
                Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")

            if mid:
                if d0.Len == 2:
                    self.subnodes.append(NodeDouble(mid).Process())
                    Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")
                elif d0.Len == 3:
                    self.subnodes.append(NodeTriple(mid).Process())
                    Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")
            if end:
                # The problem here is that any subnodes derived from <end> really belong to the parent node,
                # so we run process which updates self, but don't need to append it anywhere as it is already slated to be appended.
                self.string=end
                self.Process()
                Log(f"Process: Node #{self.subnodes[-1].id} appended to Node #{self.id}")

        # No need for a return, because of the while True: loop


class NodeContainer(Node):
    def __init__(self, s: str, nt: NodeType):
        super().__init__(s, nt)

    def __repr__(self) -> str:
        Log(f"repr(2) #{self.id}")
        r=""
        offset=" "*Node.offset
        if self.string:
            r=offset+f"Node #{self.id} -- {self.type},  '{self.string}'"
        if self.subnodes:
            Node.offset+=3
            r+=offset+f"Node #{self.id} -- {self.type}\n"+"".join([y+"\n" for y in [repr(x) for x in self.subnodes] if y])
            Node.offset-=3
        return r.rstrip()


    def PlainText(self, b: TextSpec):
        Log(f"Node(#{self.id},  {self.type}, subnodes={len(self.subnodes)}, '{self.string}'")

        indent=' '*b.indent
        if self.string:
            b.TextCtl.AppendText(indent+self.string+"\n")
        elif self.subnodes:
            self.WriteNodes(b)


    def WriteGenericNodes(self, r: TextSpec, bopen: str, bclose: str):
        indent=' '*r.indent
        # Use a compact notation for the case of a bare string inside a Double or a Triple
        if len(self.subnodes) == 1 and self.subnodes[0].type == NodeType.String:
            GenericWrite(r, indent+bopen+self.subnodes[0].string+bclose+"\n")
            return

        # Normal case
        GenericWrite(r, indent+bopen+"\n")
        r.indent+=Indent
        for x in self.subnodes:
            x.PlainText(r)
        r.indent-=Indent
        GenericWrite(r, indent+bclose+"\n")


def GenericWrite(r: TextSpec, s: str) -> None:
    r.TextCtl.AppendText(s)

#-------------------------------------------
class NodeString(NodeContainer):

    def __init__(self, s: str) -> None:
        super().__init__(s, NodeType.String)

    def WriteNodes(self, r: TextSpec):
        indent=' '*r.indent
        r.TextCtl.WriteText(indent+"'"+self.string+"\'n")


#-------------------------------------------
class NodeDouble(NodeContainer):
    def __init__(self, s: str) -> None:
        super().__init__(s, NodeType.Double)

    def __str__(self) -> str:
        s=super().__str__()
        return "{{"+s+"}}"

    def WriteNodes(self, r: TextSpec):
        super().WriteGenericNodes(r, "{{", "}}")


#-------------------------------------------
class NodeTriple(NodeContainer):
    def __init__(self, s: str) -> None:
        super().__init__(s, NodeType.Triple)

    def __str__(self) -> str:
        s=super().__str__()
        return "{{{"+s+"}}}"

    def WriteNodes(self, r: TextSpec):
        super().WriteGenericNodes(r, "{{{", "}}}")


##########################################################################
class Tokens():

    def __init__(self, s: Union[None, str, Tokens, list[Token]]=None):
        # Begin by creating a list of String tokens
        if s is None:
            self.tokens: list[Token]=[]
        elif type(s) is Tokens:
            self.tokens: list[Token]=s.tokens
        elif type(s) is list:
            self.tokens: list[Token]=s
        else:
            self.tokens: list[Token]=[TokenString(x) for x in s]

    def __str__(self) -> str:
        s="".join([str(x) for x in self.tokens])
        Log(s)
        return s

    def __getitem__(self, index: int) -> Token:
        if index < len(self.tokens):
            return self.tokens[index]
        raise IndexError

    def __len__(self) -> int:
        return len(self.tokens)

    def PlainText(self, r: TextSpec) -> None:
        for tk in self.tokens:
            tk.PlainText(r)


    def Append(self, t: Token):
        self.tokens.append(t)

    def Analyze(self):
        # Run through the list of tokens and turn any string of the form
        # N {'s
        # Tokens which are not { or }
        # N }'s
        # into a single DoubleToken or TripleToken
        rep="".join([x.rep() for x in self.tokens])
        # rep cleverly has one character for each token with the tokens hidden behind characters so we can just scan the unparsed part of the input.
        Log("Rep="+rep, Flush=True)

        m=re.search("{{{([^\{}]+)}}}", rep)
        if m is not None:
            start=m.start()
            end=m.end()
            t=TokenTriple(Tokens(self.tokens[start+3:end-3]))
            Log("Create TokenTriple: "+str(t))
            self.tokens=self.tokens[:start]+[t]+self.tokens[end:]
            self.Analyze()
            return

        m=re.search("{{\s?(if[a-z]?)\:([^\{}]+)}}", rep, flags=re.IGNORECASE)
        if m is not None:
            ts=self.tokens[m.regs[2][0]:m.regs[2][1]]     # get the tokens matched by the second group
            parts: list[Tokens]=[]
            part=Tokens()
            for i in range(len(ts)):
                if type(ts[i]) is TokenString and ts[i].value == "|":
                    parts.append(part)
                    part=Tokens()
                part.Append(ts[i])

            if len(part) > 0:
                parts.append(part)

            d=TokenIf(Tokens(parts), m.groups()[0])
            Log("Create TokenIf: "+str(d))
            self.tokens=self.tokens[:m.start()]+[d]+self.tokens[m.end():]   # We replace the whole set of tokens matched with just d
            self.Analyze()
            return

        m=re.search("{{([^\{}]+)}}", rep)
        if m is not None:
            start=m.start()
            end=m.end()
            d=TokenDouble(Tokens(self.tokens[start+2:end-2]))
            Log("Create TokenDouble: "+str(d))
            self.tokens=self.tokens[:start]+[d]+self.tokens[end:]
            self.Analyze()
            return


    # If a string token contains a list of string tokens, turn it into a single string
    def Compress(self):
        for tkn in self.tokens:
            # We have a list of tokens.  Go through it and compress each token
            tkn.Compress()


class TokenType(enum.Enum):
    StringToken=0
    DoubleToken=1
    TripleToken=2
    IfToken=3


class Token():
    def __init__(self, t: TokenType):
        self.type: TokenType=t
        self.value: str | Tokens=""

    def __str__(self) -> str:
        return "(Oops)"

    def rep(self) -> str:
        return "?"

    def IsOpen(self) -> bool:
        return False

    def IsClose(self) -> bool:
        return False

    def Compress(self):
        # A String token never contains a list of tokens
        if type(self) is TokenString:
            return

        # self.value may be a list of tokens.  If so, compress each of them
        if type(self.value.tokens) is list:
            for tkn in self.value:
                tkn.Compress()
        # Now we deal with the (now all compressed) tokens in the list
        # We merge adjacent String tokens
        tokens=self.value.tokens
        for i in range(len(tokens)-1):
            if type(tokens[i]) is TokenString and type(tokens[i+1]) is TokenString:
                # Merge token i into token i+1 and mark token for deletion
                tokens[i+1].value=tokens[i].value+tokens[i+1].value
                tokens[i]=None
        self.value.tokens=[x for x in tokens if x is not None]

    def PlainText(self, r: TextSpec) -> None:
        assert False



class TokenString(Token):
    def __init__(self, l: str | Tokens):
        super(TokenString, self).__init__(TokenType.StringToken)
        self.value=l    # Note that this can be a single character or a string of characters

    def __str__(self) -> str:
        return "".join([str(x) for x in self.value])


    def rep(self) -> str:
        if len(self.value) > 1:
            return "$"
        return str(self.value[0])

    def PlainText(self, r: TextSpec) -> None:
        r.Write(self.value)
        return

    def IsOpen(self) -> bool:
        return self.value == "{"

    def IsClose(self) -> bool:
        return self.value == "}"


class TokenIf(Token):
    def __init__(self, tkns: Tokens, tokentype: str):
        super(TokenIf, self).__init__(TokenType.IfToken)
        for t in tkns.tokens:
            if type(t) is TokenString:
                t.Compress()
        self.value: Tokens=tkns   # s is the .... contents of the {{if...}} block
        self.type: str=tokentype         # type is "if" or "ifeq" or one of the other {{}} operations

    def __str__(self) -> str:
        tokens=self.value.tokens
        if len(tokens) > 1:
            return "IF{{"+self.type+":"+" "+str(tokens[0])+" |".join([str(x) for x in tokens[1:]])+"}}IF"
        elif len(tokens) == 1:
            return "IF{{"+self.type+":"+" "+str(tokens[0])+"}}IF"
        return "IF{{}}IF"

    def rep(self) -> str:
        return "I"

    def PlainText(self, r: TextSpec) -> None:
        r.TextCtl.AppendText("{{If:")
        for tk in self.value:
            tk.PlainText(r)
        r.TextCtl.AppendText("}}")


class TokenDouble(Token):
    def __init__(self, tkns: Tokens):
        super(TokenDouble, self).__init__(TokenType.DoubleToken)
        for t in tkns.tokens:
            if type(t) is not TokenString:
                t.Compress()
        self.value=tkns    # Here s is the contents of the {{...}} block

    def __str__(self) -> str:
        return "2{{"+str(self.value)+"}}2"

    def rep(self) -> str:
        return "D"

    def PlainText(self, r: TextSpec) -> None:

        r.Write("{{")
        r.indent+=5
        for tk in self.value:
            tk.PlainText(r)
        r.indent-=5
        r.Write("}}")

class TokenTriple(Token):
    def __init__(self, tkns: Tokens):
        super(TokenTriple, self).__init__(TokenType.TripleToken)
        for t in tkns.tokens:
            if type(t) is TokenString:
                t.Compress()
        self.value=tkns    # Here s is the contents of the {{{...}}} block

    def __str__(self) -> str:
        return"3{{{"+str(self.value)+"}}}3"

    def rep(self) -> str:
        return "T"

    def PlainText(self, r: TextSpec) -> None:
        r.Write("{{{")
        r.indent+=5
        for tk in self.value:
            tk.PlainText(r)
            r.indent-=5
        r.Write("}}}")


def main():
    app=wx.App(False)
    frame=TemplateEditorFrame(None)

    app.MainLoop()
    Log("Exit mainloop")



if __name__ == "__main__":
    Indent=6
    main()