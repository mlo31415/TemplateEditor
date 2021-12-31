# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version Oct 26 2018)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class MyFrame1
###########################################################################

class MyFrame1 ( wx.Frame ):

	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"MediaWiki Template Editor", pos = wx.DefaultPosition, size = wx.Size( 1021,793 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		gSizer1 = wx.GridSizer( 1, 1, 0, 0 )

		fgSizer2 = wx.FlexGridSizer( 2, 1, 0, 0 )
		fgSizer2.SetFlexibleDirection( wx.BOTH )
		fgSizer2.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )

		bSizer2 = wx.BoxSizer( wx.VERTICAL )

		self.m_TopText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 999,150 ), wx.TE_BESTWRAP|wx.TE_MULTILINE )
		bSizer2.Add( self.m_TopText, 0, wx.ALL, 5 )


		fgSizer2.Add( bSizer2, 1, wx.EXPAND, 5 )

		gSizer2 = wx.GridSizer( 1, 2, 0, 0 )

		gSizer2.SetMinSize( wx.Size( -1,500 ) )
		self.m_bottomText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,-1 ), wx.TE_BESTWRAP|wx.TE_MULTILINE )
		self.m_bottomText.SetMinSize( wx.Size( 400,500 ) )

		gSizer2.Add( self.m_bottomText, 0, wx.ALL, 5 )

		self.m_bottomText2 = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( -1,-1 ), wx.TE_BESTWRAP|wx.TE_MULTILINE )
		self.m_bottomText2.SetMinSize( wx.Size( 400,500 ) )

		gSizer2.Add( self.m_bottomText2, 0, wx.ALL, 5 )


		fgSizer2.Add( gSizer2, 1, wx.EXPAND, 5 )


		gSizer1.Add( fgSizer2, 1, wx.EXPAND, 5 )


		self.SetSizer( gSizer1 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_SIZE, self.PanelOnSize )
		self.m_TopText.Bind( wx.EVT_TEXT, self.OnTextTop )
		self.m_bottomText.Bind( wx.EVT_TEXT, self.OnBottomText )
		self.m_bottomText2.Bind( wx.EVT_TEXT, self.OnBottomText2 )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def PanelOnSize( self, event ):
		event.Skip()

	def OnTextTop( self, event ):
		event.Skip()

	def OnBottomText( self, event ):
		event.Skip()

	def OnBottomText2( self, event ):
		event.Skip()


