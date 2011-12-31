# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# Note :
# Special variables that the context should not mess with,
#       _m, _tsshash, _tssfile
#       StringIO, tss

from  tss.functions     import *

__all__ = [ 'StackMachine', 'Namespace' ]
__all__.extend([ fn for fn in globals().keys() if fn.startswith('tss_') ])

operations = {
    '+' : lambda a, b : a + b,
    '-' : lambda a, b : a - b,
    '*' : lambda a, b : a * b,
    '/' : lambda a, b : a / b,
}

class StackMachine( object ) :
    def __init__( self, ifile, compiler, tssconfig={} ):
        self.compiler, self.tssconfig  = compiler, tssconfig
        self.encoding = compiler.encoding
        self.escfilters = tssconfig.get( 'escfilters', {} )
        self.def_escfilters = tssconfig.get('escape_filters', [])

        self.bufstack = [ [] ]
        self.ifile = ifile
        self.cssindent = u''

    #---- Stack machine instructions
 
    def setencoding( self, encoding ):
        self.encoding = encoding

    def upindent( self, up=u'' ) :
        self.cssindent += up
        return self.cssindent

    def downindent( self, down=u'' ) :
        self.cssindent = self.cssindent[:-len(down)]
        return self.cssindent

    def indent( self ) :
        return self.append( self.cssindent )

    def append( self, value ) :
        self.bufstack[-1].append( value )
        return value

    def extend( self, value ) :
        if isinstance(value, list) :
            self.bufstack[-1].extend( value )
        else :
            raise Exception( 'Unable to extend context stack' )

    def pop( self, idx=-1 ):
        return self.bufstack[-1].pop(idx)

    def pushbuf( self, buf=None ) :
        buf = []
        self.bufstack.append( buf )
        return buf

    def popbuf( self ) :
        return self.bufstack.pop(-1)

    def popbuftext( self ) :
        buf = self.popbuf()
        return u''.join( buf )

    def evalexprs( self, val, filters ) :
        text = val if isinstance(val, unicode) else str(val).decode(self.encoding)
        for filt, params in self.def_escfilters :   # default filters
            fn = self.escfilters.get( filt, None )
            text = fn.do( self, text, params ) if fn else text
        for filt, params in filters :               # evaluate filters
            fn = self.escfilters.get( filt, None )
            text = fn.do( self, text, params ) if fn else text
        return text

    def evalunary( self ):
        opr, o2 = self.pop(), self.pop()
        self.append( o2.__class__( opr + str(o2) ))

    def evalbinary( self ):
        o1, opr, o2 = self.pop(), self.pop(), self.pop()
        try    :
            print o1, o2
            self.append( operations[opr]( o1, o2 ))
        except : 
            raise
            self.append( operations[opr]( o2, o1 ))


class Namespace( object ):
    def __init__( self, parentnm, localmod ):
        self._parentnm = parentnm
        self._localmod = localmod

    def __getattr__( self, name ):
        if self._parentnm :
            return getattr(
                self._localmod, name, getattr( self._parentnm, name, None )
           )
        else :
            return getattr( self._localmod, name, None )
        
    def __setattr__( self, name, value ):
        if name in [ '_parentnm', '_localmod' ] :
            self.__dict__[name] = value
        else :
            setattr( self._localmod, name, value )
        return value

    def _linkparent( self, parentnm ):
        nm, parnm = self, self._parentnm
        while parnm : nm, parnm = parnm, parnm._parentnm
        nm._parentnm = parentnm
        return parentnm
