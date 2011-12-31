# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from   StringIO     import StringIO

prolog = """\
from   StringIO     import StringIO 
from   tss.runtime  import * 
from   tss.ast      import NUMBER_, STRING_, \\
                           EMS_, EXS_, LENGTHPX_, LENGTHCM_, LENGTHMM_, \\
                           LENGTHIN_, LENGTHPT_, LENGTHPC_, ANGLEDEG_, \\
                           ANGLERAD_, ANGLEGRAD_, TIMEMS_, TIMES_, FREQHZ_, \\
                           FREQKHZ_, PERCENTAGE_
"""

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

    #---- Python output formating methods

    def cr( self, count=1 ):
        """Move `pytext` next line preserving the current indentation"""
        self.outfd.write( '\n'*count )
        self.outfd.write( self.pyindent )

    def outline( self, line, count=1 ):
        """Do cr() and add `line` to pytext"""
        self.cr( count=count )
        self.outfd.write( line )

    def codeindent( self, up=None, down=None, indent=True ):
        """Increase current pytext indentation by `up` or `down`. If `indent`
        is True, then append pytext with new indentation space.

        flushtext() to be called to flush out the current cache of generated
        pytext."""
        self.flushtext()
        if up != None :
            self.pyindent += up
        if down != None :
            self.pyindent = self.pyindent[:-len(down)]
        if indent : 
            self.outfd.write( self.pyindent )

    def comment( self, comment, force=False ):
        if self.devmod or force :
            self.flushtext()
            self.outline( '# ' + u' '.join(comment.rstrip('\r\n').splitlines()) )

    def flushtext( self ):
        """self.optimaltext is used to maintains the list of pytext content that
        are to be flushed into the file. This list can be used for 
        local optimization"""
        if self.optimaltext :
            self.outline( '_m.extend( %s )' % self.optimaltext )
            self.optimaltext = []

    def footer( self, tsshash, tssfile ):
        self.outline( footer % (tsshash, tssfile) )

    def finish( self ):
        self.pytext = self.outfd.getvalue()

    def codetext( self ):
        return self.pytext

    #---- Stack machine instruction generator

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

    def pushbuf( self ):
        self.flushtext()
        self.outline( '_m.pushbuf()' )

    def pushtext( self, text, force=False ):
        self.optimaltext.append( text )
        force and self.flushtext()

    def pushobj( self, objstr ):
        self.flushtext()
        self.outline( '_m.append( %s )' % objstr )

    def popappend( self, astext=True ):
        self.flushtext()
        if astext == True :
            self.outline( '_m.append( _m.popbuftext() )' )
        else :
            self.outline( '_m.append( _m.popbuf() )' )

    def putstatement( self, stmt ):
        self.flushtext()
        self.outline( stmt.rstrip('\r\n') )

    def popreturn( self, astext=True ):
        self.flushtext()
        if astext == True :
            self.outline( 'return _m.popbuftext()' )
        else :
            self.outline( 'return _m.popbuf()' )

    def evalfun( self, fncall ):
        """Evaluate `fncall` string and push the resulting string value into
        stack."""
        self.flushtext()
        self.outline( '_m.append( _m.evalexprs( %s, "" ))' % fncall.strip() )

    def evalunary( self ):
        self.outline( '_m.evalunary()' )

    def evalbinary( self ):
        self.outline( '_m.evalbinary()' )
