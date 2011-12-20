# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   StringIO     import StringIO

prolog = """\
from   StringIO     import StringIO 
from   tss.runtime  import * """

footer = """\
_tsshash = %r
_tssfile = %r """

class InstrGen( object ) :
    machname = '_m'

    def __init__( self, compiler, tssconfig={} ):
        self.compiler = compiler
        self.tssconfig = tssconfig
        self.devmod = self.tssconfig['devmod']
        self.outfd = StringIO()
        self.pyindent = u''
        self.optimaltext = []
        self.pytext = None
        # prolog for python translated template
        self.encoding = compiler.encoding

    def __call__( self ):
        return InstrGen( self.compiler, tssconfig=self.tssconfig )

    def cr( self, count=1 ):
        self.outfd.write( '\n'*count )
        self.outfd.write( self.pyindent )

    def outline( self, line, count=1 ):
        self.cr( count=count )
        self.outfd.write( line )

    def codeindent( self, up=None, down=None, indent=True ):
        self.flushtext()
        if up != None :
            self.pyindent += up
        if down != None :
            self.pyindent = self.pyindent[:-len(down)]
        if indent : 
            self.outfd.write( self.pyindent )

    def codetext( self ):
        return self.pytext

    #---- Generate Instructions

    def initialize( self ):
        self.outfd.write( prolog )
        self.cr()

    def indent( self ):
        if self.uglyhtml == False :
            self.flushtext()
            self.outline( '_m.indent()' )

    def upindent( self, up=u'' ):
        if self.uglyhtml == False :
            self.flushtext()
            self.outline( '_m.upindent( up=%r )' % up )

    def downindent( self, down=u'' ):
        if self.uglyhtml == False :
            self.flushtext()
            self.outline( '_m.downindent( down=%r )' % down )

    def comment( self, comment, force=False ):
        if self.devmod or force :
            self.flushtext()
            self.outline( '# ' + u' '.join(comment.rstrip('\r\n').splitlines()) )

    def flushtext( self ):
        if self.optimaltext :
            self.outline( '_m.extend( %s )' % self.optimaltext )
            self.optimaltext = []

    def puttext( self, text, force=False ):
        self.optimaltext.append( text )
        force and self.flushtext()

    def putstatement( self, stmt ):
        self.flushtext()
        self.outline( stmt.rstrip('\r\n') )

    def evalexprs( self, code, filters ):
        code = code.strip()
        if code :
            self.flushtext()
            self.outline('_m.append( _m.evalexprs(%s, %s) )' % (code, filters))

    def evalfunc( self, fncall ):
        fncall = fncall.strip()
        if fncall :
            self.flushtext()
            self.outline( '_m.append( %s )' % fncall )

    def pushbuf( self ):
        self.flushtext()
        self.outline( '_m.pushbuf()' )

    def popappend( self, astext=True ):
        self.flushtext()
        if astext == True :
            self.outline( '_m.append( _m.popbuftext() )' )
        else :
            self.outline( '_m.append( _m.popbuf() )' )

    def popreturn( self, astext=True ):
        self.flushtext()
        if astext == True :
            self.outline( 'return _m.popbuftext()' )
        else :
            self.outline( 'return _m.popbuf()' )

    def footer( self, tsshash, tssfile ):
        self.outline( footer % (tsshash, tssfile) )

    def finish( self ):
        self.pytext = self.outfd.getvalue()
