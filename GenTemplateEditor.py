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
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"MediaWiki Template Editor", pos = wx.DefaultPosition, size = wx.Size( 1021,622 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

		self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

		gSizer1 = wx.GridSizer( 3, 1, 0, 0 )

		self.m_TopText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 999,100 ), wx.TE_BESTWRAP|wx.TE_MULTILINE )
		gSizer1.Add( self.m_TopText, 0, wx.ALL, 5 )

		self.m_staticline1 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		gSizer1.Add( self.m_staticline1, 0, wx.EXPAND |wx.ALL, 5 )

		self.m_BottomText = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 999,100 ), wx.TE_BESTWRAP|wx.TE_MULTILINE )
		gSizer1.Add( self.m_BottomText, 0, wx.ALL, 5 )


		self.SetSizer( gSizer1 )
		self.Layout()

		self.Centre( wx.BOTH )

		# Connect Events
		self.Bind( wx.EVT_SIZE, self.PanelOnSize )
		self.m_TopText.Bind( wx.EVT_TEXT, self.OnTextTop )
		self.m_BottomText.Bind( wx.EVT_CHAR, self.OnCharBottom )
		self.m_BottomText.Bind( wx.EVT_TEXT, self.OnTextBottom )

	def __del__( self ):
		pass


	# Virtual event handlers, overide them in your derived class
	def PanelOnSize( self, event ):
		event.Skip()

	def OnTextTop( self, event ):
		event.Skip()

	def OnCharBottom( self, event ):
		event.Skip()

	def OnTextBottom( self, event ):
		event.Skip()


