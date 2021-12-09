# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version Oct 26 2018)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.richtext

###########################################################################
## Class MyFrame1
###########################################################################

class MyFrame1 ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"MediaWiki Template Editor", pos = wx.DefaultPosition, size = wx.Size( 1021,793 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		gSizer1 = wx.GridSizer( 1, 1, 0, 0 )

		fgSizer1 = wx.FlexGridSizer( 2, 1, 0, 0 )
		fgSizer1.SetFlexibleDirection( wx.BOTH )
		fgSizer1.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		self.m_TopText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 999,150 ), wx.TE_BESTWRAP|wx.TE_MULTILINE )
		fgSizer1.Add( self.m_TopText, 0, wx.ALL, 5 )

		self.m_richText1 = wx.richtext.RichTextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,999 ), 0|wx.VSCROLL|wx.HSCROLL|wx.NO_BORDER|wx.WANTS_CHARS )
		fgSizer1.Add( self.m_richText1, 1, wx.EXPAND |wx.ALL, 5 )


		gSizer1.Add( fgSizer1, 1, wx.EXPAND, 5 )


		self.SetSizer( gSizer1 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_SIZE, self.PanelOnSize )
		self.m_TopText.Bind( wx.EVT_TEXT, self.OnTextTop )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def PanelOnSize( self, event ):
		event.Skip()

	def OnTextTop( self, event ):
		event.Skip()


