# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

# Note :
# Special variables that the context should not mess with,
#       _m, _tsshash, _tssfile
#       StringIO, tss

__all__ = [ 'StackMachine', 'Namespace',
            'EMS_', 'EXS_', 'LENGTHPX_', 'LENGTHCM_', 'LENGTHMM_', 'LENGTHIN_',
            'LENGTHPT_', 'LENGTHPC_', 'ANGLEDEG_', 'ANGLERAD_', 'ANGLEGRAD_',
            'TIMEMS_', 'TIMES_', 'FREQHZ_', 'FREQKHZ_', 'PERCENTAGE_',
            'NUMBER_', 'STRING_'
          ]
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
        rc = u''
        for x in buf :
            rc += x if isinstance(x, basestring) else unicode(x)
        return rc

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
        o1, opr = self.pop(), self.pop()
        self.append( o1.__class__( opr + str(o1) ))

    def evalbinary( self ):
        o2, opr, o1 = self.pop(), self.pop(), self.pop()
        try    :
            self.append( operations[opr.strip()]( o1, o2 ))
        except : 
            raise
            self.append( operations[opr.strip()]( o2, o1 ))


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


#---- Expression Terms

class DIMENSION_( object ):
    suffix = u''
    def __init__( self, value ):
        self.val = value

    def __str__( self ):
        return self.val

    def value( self ):
        t = self.val
        return float(t) if '.' in t else int(t)

    def __add__( self, y ):
        return self.__class__( str(self.value()+y.value()) + self.suffix )

    def __sub__( self, y ):
        return self.__class__( str(self.value()-y.value()) + self.suffix )

    def __mul__( self, y ):
        return self.__class__( str(self.value()*y.value()) + self.suffix )

    def __div__( self, y ):
        return self.__class__( str(self.value()/y.value()) + self.suffix )

class EMS_( DIMENSION_ ):
    suffix = 'em'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class EXS_( DIMENSION_ ):
    suffix = 'ex'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class LENGTHPX_( DIMENSION_ ):
    suffix = 'px'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class LENGTHCM_( DIMENSION_ ):
    suffix = 'cm'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class LENGTHMM_( DIMENSION_ ):
    suffix = 'mm'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class LENGTHIN_( DIMENSION_ ):
    suffix = 'in'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class LENGTHPT_( DIMENSION_ ):
    suffix = 'pt'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class LENGTHPC_( DIMENSION_ ):
    suffix = 'pc'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class ANGLEDEG_( DIMENSION_ ):
    suffix = 'deg'
    def value( self ):
        t = self.val[:-3]
        return float(t) if '.' in t else int(t)

class ANGLERAD_( DIMENSION_ ):
    suffix = 'rad'
    def value( self ):
        t = self.val[:-3]
        return float(t) if '.' in t else int(t)

class ANGLEGRAD_( DIMENSION_ ):
    suffix = 'grad'
    def value( self ):
        t = self.val[:-4]
        return float(t) if '.' in t else int(t)

class TIMEMS_( DIMENSION_ ):
    suffix = 'ms'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class TIMES_( DIMENSION_ ):
    suffix = 's'
    def value( self ):
        t = self.val[:-1]
        return float(t) if '.' in t else int(t)

class FREQHZ_( DIMENSION_ ):
    suffix = 'Hz'
    def value( self ):
        t = self.val[:-2]
        return float(t) if '.' in t else int(t)

class FREQKHZ_( DIMENSION_ ):
    suffix = 'kHz'
    def value( self ):
        t = self.val[:-3]
        return float(t) if '.' in t else int(t)

class PERCENTAGE_( DIMENSION_ ):
    suffix = '%'
    def value( self ):
        t = self.val[:-1]
        return float(t) if '.' in t else int(t)

class NUMBER_( object ):
    suffix = ''
    def __init__( self, value ):
        self.val = value

    def __str__( self ):
        return str(self.val)

    def value( self ):
        t = self.val
        return float(t) if '.' in t else int(t)

    def __add__( self, y ):
        if isinstance(y, STRING_) :
            return y.__class__( self.value()+y.value(), y.wrap )
        else :
            return self.__class__( str(self.value()+y.value()) + y.suffix )

    def __sub__( self, y ):
        if isinstance(y, STRING_) :
            return y.__class__( self.value()-y.value(), y.wrap )
        else :
            return self.__class__( str(self.value()-y.value()) + y.suffix )

    def __mul__( self, y ):
        if isinstance(y, STRING_) :
            return y.__class__( self.value()*y.value(), y.wrap )
        else :
            return self.__class__( str(self.value()*y.value()) + y.suffix )

    def __div__( self, y ):
        if isinstance(y, STRING_) :
            return y.__class__( Sself.value()/y.value(), y.wrap )
        else :
            return self.__class__( str(self.value()/y.value()) + y.suffix )

class STRING_( object ):
    suffix = u''
    def __init__( self, value, wrap=None ):
        self.val = (wrap + value + wrap) if wrap else value
        self.wrap = self.val[0]

    def __str__( self ):
        return self.val

    def value( self ):
        return self.val[1:-1]

    def __add__( self, y ):
        return self.__class__( self.value()+y.value(), self.wrap )

    def __sub__( self, y ):
        return self.__class__( self.value()-y.value(), self.wrap )

    def __mul__( self, y ):
        return self.__class__( self.value()*y.value(), self.wrap )

    def __div__( self, y ):
        return self.__class__( self.value()/y.value(), self.wrap )

