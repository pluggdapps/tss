# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2010 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Module containing Node definition for all terminal and non-teminals nodes.

The AST tree is constructed according to the grammar. From the root
non-terminal use the children() method on every node to walk through the tree.

To walk throug the AST,
  * parse() the text, which returns the root non-terminal
  * Use children() method on every non-terminal node.

validate :
  * Check for @media nesting within @media `rulesets.
  * Check for @page nesting within @page `block`.

headpass1 :
  * nestedrules, bubble up rulesets, after merging with parent selectors, to
    the root node.

headpass2 :
  * igen.initialize() done by Root node.
  * parse @charset for encoding string, to be stored in igen.encoding,
    generating,
        "-*- coding: %s -*-" % igen.encoding
        "_m.setencoding( %r )" % igen.encoding

generate :
  * Generate StackMachine instruction in python

tailpass :
  * Create footer for `tsshash` and `tssfile`
  * finish.
"""

# Gotcha : None
# Notes  : None
# Todo   : None

import sys, re
from   copy             import deepcopy
from   tss.utils        import charset, throw

class ASTError( Exception ):
    pass


class Context( object ):
    def __init__( self, htmlindent=u'' ):
        self.htmlindent = htmlindent


# ------------------- AST Nodes (Terminal and Non-Terminal) -------------------

class Node( object ):

    def __init__( self, parser ):
        self.parser = parser
        self.parent = None

    def __call__( self ):
        fn = lambda o : o if o == None else o()
        args = map( fn, [ getattr( self, x ) for x in self.rhs ])
        return self.__class__( self.parser, *args )

    def children( self ):
        """Tuple of childrens in the same order as parsed by the grammar rule.
        """
        return tuple()

    def safedesc( self ):
        """Normally to descend a sub-tree, function calls are recursively 
        applied on the tuple returned by self.children(). Such recursions
        can lead to stack-overflow. To avoid such scenario, use safedesc()
        which will flatten left-recursion based on `flattenrule` if
        defined."""
        return tuple()

    def validate( self, table ):
        """Validate this node and all the children nodes. Expected to be called
        before processing the nodes.
        
        If no issue with validation, returns True"""
        return True

    def importast( self, igen, table ):
        """Process @import directive and Compile importable .tss files and 
        pull relevant AST from them."""

    def nestedrulesets( self, igen, table ):
        """Unwind nested rulesets."""

    def extendrule( self, igen, table ):
        """Process @extend directive."""

    def headpass1( self, igen, table ):
        """Pre-processing phase 1, useful to implement multi-pass compilers"""
        [ x.headpass1( igen, table ) for x in self.safedesc() ]

    def headpass2( self, igen, table ):
        """Pre-processing phase 2, useful to implement multi-pass compilers"""
        [ x.headpass2( igen, table ) for x in self.safedesc() ]

    def generate( self, igen, table ):
        """Code generation phase. The result must be an executable python
        script"""
        [ x.generate( igen, table ) for x in self.safedesc() ]

    def tailpass( self, igen, table ):
        """Post-processing phase 1, useful to implement multi-pass compilers"""
        [ x.tailpass( igen, table ) for x in self.safedesc() ]

    def dump( self, table ):
        """Simply dump the contents of this node and its children node and
        return the same."""
        return u''.join([ x.dump(table) for x in self.safedesc() ])

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        """ Pretty print the Node and all its attributes and children
        (recursively) to a buffer.
            
        buf:   
            Open IO buffer into which the Node is printed.
        
        offset: 
            Initial offset (amount of leading spaces) 
        
        attrnames:
            True if you want to see the attribute names in name=value pairs.
            False to only see the values.
        
        showcoord:
            Do you want the coordinates of each Node to be displayed.
        """

    #---- Helper methods

    def stackcompute( self, igen, compute, astext=True ):
        """Push a new buf, execute the compute function, pop the buffer and
        append that to the parent buffer."""
        igen.pushbuf()
        compute()
        igen.popappend( astext=astext )
        return None

    def getroot( self ):
        """Get root node traversing backwards from this `self` node."""
        node = self
        parent = node.parent
        while parent : node, parent = parent, parent.parent
        return node

    def matchdown( self, classes ):
        """Traverse down the sub-tree to find a match in list of `classes`,
        and return a list of matching nodes."""
        cls, l = self.__class__, []
        l.append( (cls, self) ) if cls in classes else None
        [ l.extend( x.matchdown(classes) ) for x in self.safedesc() ]
        return l

    def matchup( self, classes ):
        """Traverse up the tree, through node parent to find a match in list
        of `classes`, and return a list of matching nodes."""
        l, node = [], self
        check = lambda cls, n : l.append((cls, n)) if cls in classes else None
        while node :
            check( type(node), node )
            node = node.parent
        return l

    def allterminals( self ):
        """Return a list of all terminals under the node's subtree"""
        ts = []
        [ ts.extend( x.allterminals() ) for x in self.safedesc() ]
        return ts

    def compare( self, other, ws=True ):
        """Check whether the non-terminals are of same type,
        if so, same number of children, if so, their terminals compare True."""
        if type(self) != type(other) : return False
        if len(self.safedesc()) != len(other.safedesc()) : return False
        return all([
            x.compare(y) for x,y in zip( self.safedesc(), oss.safedesc() )
        ])

    @classmethod
    def setparent( cls, parnode, childnodes ):
        [ setattr( n, 'parent', parnode ) for n in childnodes ]


class Terminal( Node ) :
    """Abstract base class for Tayra style's AST terminal nodes."""

    def __init__( self, parser=None, terminal=u'', **kwargs ):
        Node.__init__( self, parser )
        if not isinstance( terminal, basestring ) :
            raise Exception( 'Only set self.terminal to basestring' )
        self.terminal = terminal
        [ setattr( self, k, v ) for k,v in kwargs.items() ]

    def __repr__( self ):
        return unicode( self.terminal )

    def __str__( self ):
        return unicode( self.terminal )

    def __call__( self ):
        return self.__class__( self.parser, self.terminal )

    def generate( self, igen, table ):
        """Dump the content."""
        igen.pushtext( self.dump(table) )

    def dump( self, table ):
        """Simply dump the contents of this node and its children node and
        return the same."""
        return self.terminal

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        """ Pretty print the Node and all its attributes and children
        (recursively) to a buffer.
            
        buf:   
            Open IO buffer into which the Node is printed.
        
        offset: 
            Initial offset (amount of leading spaces) 
        
        attrnames:
            True if you want to see the attribute names in name=value pairs.
            False to only see the values.
        
        showcoord:
            Do you want the coordinates of each Node to be displayed.
        """
        lead = ' ' * offset
        buf.write(lead + '<%s>: %r' % (self.__class__.__name__, self.terminal))
        buf.write('\n')

    #---- Helper methods

    def compare( self, other, ws=True ):
        """Check whether the terminals match with or without whitespace"""
        if type(self) != type(other) : return False
        if ws and (self.dump({}) != other.dump({}) ): return False
        if self.dump({}).strip(' \t\r\n\f') != other.dump({}).strip(' \t\r\n\f'):
            return False
        return True

    def lstrip( self, chars ):
        """Strip off the leftmost characters from the terminal string. Return
        the remaining characters.
        """
        self.terminal = self.terminal.lstrip( chars )
        return self.terminal

    def rstrip( self, chars ):
        """Strip off the rightmost characters from the terminal string. Return
        the remaining characters.
        """
        self.terminal = self.terminal.rstrip( chars )
        return self.terminal


class NonTerminal( Node ):      # Non-terminal
    """Abstract base class for Tayra Style's AST non-terminalnodes."""

    def __init__( self, *args, **kwargs ) :
        parser = args[0]
        Node.__init__( self, parser )
        self._terms, self._nonterms = tuple(), tuple()

    def safedesc( self ):
        """Normally to descend a sub-tree, function calls are recursively 
        applied on the tuple returned by self.children(). Such recursions
        can lead to stack-overflow. To avoid such scenario, use safedesc()
        which will flatten left-recursion based on `flattenrule` if
        defined."""
        if hasattr( self, 'flattenrule' ):
            return tuple( self.flatten( *self.flattenrule ))
        else :
            return self.children()

    def validate( self, table ):
        """Validate this node and all the children nodes. Expected to be called
        before processing the nodes.
        
        If no issue with validation, returns True"""
        return all([ x.validate( table ) for x in self.safedesc() ])

    def lstrip( self, chars ):
        """Strip off the leftmost characters from children nodes. Stop
        stripping on recieving non null string."""
        value = u''
        for c in self.safedesc() :
            value = c.lstrip( chars )
            if value : break
        return value

    def rstrip( self, chars ):
        """Strip off the rightmost characters from children nodes. Stop
        stripping on recieving non null string."""
        value = u''
        children = list(self.safedesc())
        children.reverse()
        for c in children :
            value = c.rstrip( chars )
            if value : break
        return value

    def flatten( self, attrnode, attrs ):
        """Instead of recursing through left-recursive grammar, flatten them
        into sequential list for looping on them later."""
        node, rclist = self, []

        if isinstance(attrs, basestring) :
            fn = lambda n : [ getattr(n, attrs) ]
        elif isinstance(attrs, (list,tuple)) :
            fn = lambda n : [ getattr(n, attr) for attr in attrs ]
        else :
            fn = attrs

        while node :
            rclist.extend( filter( None, list(fn(node))) )
            node = getattr(node, attrnode)
        rclist.reverse()
        return rclist

    def delete( self, lrchild ):
        """Unlink this node from AST and relink its left-recursive child with
        its left-recursive parent."""
        parent, rechild, self.parent = self.parent, getattr(self, lrchild), None
        if parent :
            obj = getattr( parent, lrchild )
            if obj != self :
                raise Exception('%s node is not left-recursive !?' % obj)
            setattr( parent, lrchild, rechild )
        rechild.parent = parent
        setattr( self, lrchild, None )

    def insertafter( self, node, lrchild ):
        """Insert `node` as left-recursive child to this node."""
        rechild = getattr( self, lrchild )
        setattr( self, lrchild, node )
        node.parent = self
        setattr( node, lrchild, rechild )
        rechild.parent = node

    def insertbefore( self, node, lrchild ):
        """Insert `node` as left-recursive child to this parent node."""
        setattr( self.parent, lrchild, node )
        node.parent = self.parent
        setattr( node, lrchild, self )
        self.parent = node

    def tailinsert( self, node, lrchild ):
        """Insert `node` at the end of the left-recursive tree."""
        tail = self
        while getattr(tail, lrchild) : tail = getattr( tail, lrchild )
        setattr( tail, lrchild, node )
        node.parent = tail

    def insertsubtree( self, node, lrchild ):
        """Insert node and its entire left-recursive subtree to this
        left-recursive node."""
        rechild = getattr( self, lrchild )
        setattr( self, lrchild, node )
        node.parent = self
        node.tailinsert( rechild, lrchild )

    def collect( self, lrchild, childattr ):
        """Collect all children as a list of tuple from left-recursive tree."""
        node = self
        rc = []
        while node :
             rc.append( tuple([ getattr( node, x ) for x in childattr ]) )
             node = getattr( node, lrchild )
        return rc



# ------------------- Non-terminal classes ------------------------

class Tss( NonTerminal ):
    """class to handle `tss` grammar."""

    flattenrule = ('tss', 'nonterm')
    rhs = ('tss', 'nonterm')

    def __init__( self, parser, tss, nonterm ) :
        NonTerminal.__init__( self, parser, tss, nonterm )
        self._nonterms = self.tss, self.nonterm = tss, nonterm
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

        # Initialization
        self.blocks = []    # List of all styling blocks { ... }
        self.table = {
            'nestedrules' : { 'insels' : [] },
            'signature' : u'',
            'expreval' : False.
        }

    def _hascontent( self ) :
        """Check whether the main of the template page contains valid content,
        if not then the `main` function should not be generated at all."""
        return True

    def _main( self, igen, table ):
        """Generate the main function only when there is valid content in the
        global scope.
        """
        igen.cr()
        if self._hascontent() :
            # main function signature
            signature = table['signature'].strip(', \t')
            u', '.join([ signature, u'*args', u'**kwargs' ])
            igen.putstatement( u"def main( %s ) :" % signature )
            igen.codeindent( up=u'  ' )

            # Main function's children
            igen.pushbuf()
            [ x.generate(igen, table) for x in self.safedesc() ]
            igen.flushtext()

            # finish main function
            igen.popreturn( astext=True )
            igen.codeindent( down='  ' )
        else :
            igen.flushtext()

    def children( self ):
        return self._nonterms

    def validate( self, table={} ):
        rc = all([ x.validate(table) for x in self.safedesc() ])
        if rc == False : raise Exception('Validation failed')
        return True

    def asttransorms( self, igen, table ):
        NonTerminal.importast( self, igen, table )
        NonTerminal.nestedrulesets( self, igen, table )
        NonTerminal.extendrule( self, igen, table )

    def headpass2( self, igen, table={} ):
        igen.initialize()
        NonTerminal.headpass2( self, igen, table )

    def generate( self, igen, table={} ):
        table_ = deepcopy( table )
        table_.update( table )
        self.asttransorms( igen, table_ )
        self.headpass1( igen, table_ )
        self.headpass2( igen, table_ )
        self._main( igen, table_ )
        self.tailpass( igen, table_ )

    def tailpass( self, igen, table={} ):
        igen.cr()
        [ x.tailpass( igen, table ) for x in self.safedesc() ]
        igen.comment( u"---- Footer", force=True )
        igen.footer( table['tsshash'], table['tssfile'] )
        igen.finish()

    def dump( self, table={} ):
        return u''.join([ x.dump(table) for x in self.safedesc() ])

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + '-->tss: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+5, attrnames, showcoord) for x in self.safedesc() ]


#---- CDATA

class Cdata( NonTerminal ):
    """class to handle `cdata` grammar."""

    rhs = ('CDO', 'CDATATEXT', 'CDC')

    def __init__( self, parser, cdo, cdatatext, cdc ) :
        NonTerminal.__init__( self, parser, cdo, cdatatext, cdc )
        self._terms = self.CDO, self.CDATATEXT, self.CDC = cdo, cdatatext, cdc
        self._terms = filter( None, self._terms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self._terms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'cdata: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#--- @Charset

class Charset( NonTerminal ):
    """class to handle `charset` grammar."""

    rhs = ('CHARSET_SYM', 'string', 'SEMICOLON')

    def __init__( self, parser, sym, string, semi ) :
        NonTerminal.__init__( self, parser, sym, string, semi )
        self._terms = self.CHARSET_SYM, self.SEMICOLON = sym, semi
        self._nonterms = (self.string,) = (string,)
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self.CHARSET_SYM, self.string, self.SEMICOLON

    def headpass2( self, igen, table ):
        igen.encoding = charset(
            parseline=self.dump(table), encoding=self.parser.tssparser.encoding )
        igen.comment( u"-*- coding: %s -*-" % igen.encoding, force=True )
        igen.putstatement( u"_m.setencoding( %r )" % igen.encoding )
        NonTerminal.headpass2( self, igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'charset: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- @namespace

class Namespace( NonTerminal ):
    """class to handle `namespace` grammar."""

    rhs = ('NAMESPACE_SYM', 'prefix', 'nonterm', 'SEMICOLON')

    def __init__( self, parser, sym, prefix, nonterm, semi ) :
        NonTerminal.__init__( self, parser, sym, prefix, nonterm, semi )
        self._terms = self.NAMESPACE_SYM, self.SEMICOLON = sym, semi
        self._terms = filter( None, self._terms )
        self._nonterms = self.prefix, self.nonterm = prefix, nonterm
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = self.NAMESPACE_SYM, self.prefix, self.nonterm, self.SEMICOLON
        return filter( None, x )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'namespace: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- @font_face

class FontFace( NonTerminal ) :
    """class to handle `font_face` grammar."""

    rhs = ('FONT_FACE_SYM', 'block')

    def __init__( self, parser, sym, block ) :
        NonTerminal.__init__( self, parser, sym, block )
        self._terms = (self.FONT_FACE_SYM,) = (sym,)
        self._nonterms = (self.block,) = (block,)
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self.FONT_FACE_SYM, self.block

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'font_face: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- @media

class Media( NonTerminal ):
    """class to handle `media` grammar."""

    rhs = ('MEDIA_SYM', 'mediums', 'exprs', 'openbrace', 'rulesets', 'closebrace')

    def __init__( self, parser, sym, mediums, exprs, obrace, rulesets, cbrace ):
        NonTerminal.__init__(
            self, parser, sym, mediums, exprs, obrace, rulesets, cbrace )
        self._terms = (self.MEDIA_SYM,) = (sym,)
        self._terms = filter( None, self._terms )
        self._nonterms = \
            self.mediums, self.exprs, self.openbrace, self.rulesets, self.closebrace = \
                mediums, exprs, obrace, rulesets, cbrace
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ) :
        x = ( self.MEDIA_SYM, self.mediums, self.exprs,
              self.openbrace, self.rulesets, self.closebrace )
        return filter(None, x)

    def validate( self, table ):
        if filter( None, [ x.matchdown((Media,)) for x in self.safedesc() ]) :
            raise Exception('`@media` rule cannot be nested')
        return all([ x.validate(table) for x in self.safedesc() ])

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'media: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Mediums( NonTerminal ):
    """class to handle `mediums` grammar."""

    flattenrule = ('mediums', ('S', 'medium', 'COMMA'))
    rhs = ('mediums', 'COMMA', 'medium', 'S')

    def __init__( self, parser, mediums, comma, medium, s ) :
        NonTerminal.__init__( self, parser, mediums, comma, medium, s )
        self._terms = self.S, self.COMMA = s, comma
        self._terms = filter( None, self._terms )
        self._nonterms = self.mediums, self.medium = mediums, medium
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.mediums, self.COMMA, self.medium, self.S) )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        [ x.show(buf, offset, attrnames, showcoord) for x in self.safedesc() ]

    def pushident( self, mediums ):
        if self.mediums : self.mediums.pushident( mediums )
        else : self.mediums = mediums


#---- @page

class Page( NonTerminal ) :
    """class to handle `page` grammar."""

    rhs = ('PAGE_SYM', 'ident1', 'COLON', 'ident2', 'block')

    def __init__( self, parser, sym, ident1, colon, ident2, block ) :
        NonTerminal.__init__( self, parser, sym, ident1, colon, ident2, block )
        self._terms = self.PAGE_SYM, self.COLON = sym, colon
        self._terms = filter( None, self._terms )
        self._nonterms = \
            self.ident1, self.ident2, self.block = ident1, ident2, block
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = ( self.PAGE_SYM, self.ident1, self.COLON, self.ident2, self.block )
        return filter( None, x )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False) :
        lead = ' ' * offset
        buf.write( lead + 'page: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class PageMargin( NonTerminal ):
    """class to handler `pagemargin` grammar."""

    rhs = ('PAGE_MARGIN_SYM', 'block')

    def __init__( self, parser, pagemargin, block ):
        NonTerminal.__init__( self, parser, pagemargin, block )
        self._terms = (self.PAGE_MARGIN_SYM,) = (pagemargin,)
        self._nonterms = (self.block,) = (block,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.PAGE_MARGIN_SYM, self.block) )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False) :
        lead = ' ' * offset
        buf.write( lead + 'pagemargin: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- @generic-atrule

class AtRule( NonTerminal ) :
    """class to handle `atrule` grammar."""

    rhs = ('ATKEYWORD', 'expr', 'block', 'SEMICOLON', 'ruleblock')

    def __init__( self, parser, sym, expr, block, semi, ruleblock ) :
        NonTerminal.__init__(self, parser, sym, expr, block, semi, ruleblock)
        self._terms = self.ATKEYWORD, self.SEMICOLON = sym, semi
        self._terms = filter( None, self._terms )
        # Expand ruleblock.
        ruleblock = ruleblock or (None, None, None)
        self.openbrace, self.rulesets, self.closebrace = ruleblock
        # Non terminals
        self.expr, self.block, self.ruleblock = expr, block, ruleblock
        self._nonterms = \
            self.expr, self.block, self.openbrace,self.rulesets,self.closebrace
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = ( self.ATKEYWORD, self.expr, self.block, self.SEMICOLON,
              self.openbrace, self.rulesets, self.closebrace )
        return filter( None, x )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'atrule: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- @Import

class Import( NonTerminal ) :
    """class to handle `import` grammar."""

    rhs = ('IMPORT_SYM', 'nonterm', 'mediums', 'SEMICOLON')

    def __init__( self, parser, sym, nonterm, mediums, semi ) :
        NonTerminal.__init__( self, parser, sym, nonterm, mediums, semi )
        self._terms = self.IMPORT_SYM, self.SEMICOLON = sym, semi
        self._terms = filter( None, self._terms )
        self._nonterms = self.nonterm, self.mediums = nonterm, mediums
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )
        self.skipgen = False

    #---- Methods to merge imported AST with importing AST

    def _nodirectives( self, tu ):
        # No charset or namespace directives allowed
        x = tu.matchdown( (Charset, Namespace) )
        if x :
            err = '%s directives not allowed in imported tss file' % x
            raise Exception( err )

    def _pull_directives( self, tu ):
        ds = map( lambda x : x[1], tu.matchdown((FontFace,Media,Page,Atrule)) )
        _, ss = self.matchup( (Tss,) )[0]
        ds.reverse()
        [(d.parent.delete('tss'), ss.insertafter(d.parent, 'tss')) for d in ds]

    def _pull_rulesets( self, tu ):
        rs = filter( lambda x : isinstance(x, Rulesets),
                     map( lambda x : x.nonterm, tu.matchdown((Tss,)) ) )
        rulesets = rs.pop(0) if rs else None
        [ rulesets.tailinsert( r, 'rulesets' ) for r in rs ]
        # self.parent should be `rulesets`
        self.parent.insertsubtree( rulesets, 'rulesets' )

    def _mergeast( self, tu ):
        self._nodirective( tu )
        self._pull_directives( tu )
        self._pull_rulesets( tu )

    def _importtss( self, text ):
        """Strings begining with http:// or url( will not be imported
        Strings ending with .css will not be imported."""
        text = text.strip('"\' \t')
        x = text.startswith('http://') or text.startswith('url(')
        return '' if x or self.mediums or text.endswith('.css') else text

    #---- Import TSS files.

    def children( self ) :
        x = self.IMPORT_SYM, self.nonterm, self.mediums, self.SEMICOLON
        return filter( None, x )

    def importast( self, igen, table ):
        from  tss.compiler import Compiler
        tssconfig = self.parser.tssparser.tssconfig
        tssloc = self._importtss( self.nonterm.dump( table ))
        if tssloc :
            comp = Compiler( tssloc=tssloc, tssconfig=tssconfig )
            tu = comp.toast() 
            self._mergeast( tu )
            self.IMPORT_SYM, self.nonterms, self.mediums, self.SEMICOLON = \
                None, None, None, None

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'import: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- @extend

class Extend( NonTerminal ) :
    """class to handle `extend` grammar."""

    rhs = ('EXTEND_SYM', 'selectors', 'SEMICOLON', 'wc')

    def __init__( self, parser, sym, selectors, semi, wc ) :
        NonTerminal.__init__( self, parser, sym, selectors, semi, wc )
        self._terms = self.EXTEND_SYM, self.SEMICOLON = sym, semi
        self._terms = filter( None, self._terms )
        self._nonterms = self.selectors, self.wc = selectors, wc
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = self.EXTEND_SYM, self.selectors, self.SEMICOLON, self.wc
        return filter( None, x )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False) :
        lead = ' ' * offset
        buf.write( lead + 'extend: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- Rulesets

class Rulesets( NonTerminal ):
    """class to handle `rulesets` grammar."""

    flattenrule = ('rulesets', 'nonterm')
    rhs = ('rulesets', 'nonterm')

    def __init__( self, parser, rulesets, nonterm ) :
        NonTerminal.__init__( self, parser, rulesets, nonterm )
        self._nonterms = self.rulesets, self.nonterm = rulesets, nonterm
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def nestedrulesets( self, igen, table ):
        contr = self.matchup((Ruleset,))
        contr and contr[0][1].rulesets.append( self )

    def children( self ):
        return self._nonterms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        [ x.show(buf, offset, attrnames, showcoord) for x in self.safedesc() ]


class Ruleset( NonTerminal ):
    """class to handle `ruleset` grammar."""

    rhs = ('selectors', 'block')

    def __init__( self, parser, selectors, block ) :
        NonTerminal.__init__( self, selectors, block )
        self._nonterms = self.selectors, self.block = selectors, block
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )
        self.rulesets = []

    def children( self ):
        return filter( None, (self.selectors, self.block) )

    def nestedrulesets( self, igen, table ):
        nestedtbl = table['nestedrules']
        # Merge nested selectors for `this` ruleset
        insels = nestedtbl['insels']
        clone = self.selectors()
        clone.parent = None
        if self.selectors and insels :
            selectors = None
            while nestedtbl['insels'] :
                (selectors or self.selectors).nestedrulesets( igen, table )
                if selectors :
                    self.selectors.tailinsert( selectors, 'selectors' )
                    selectors.parent.COMMA = comma
                selectors = clone()
                nestedtbl['insels'] = nestedtbl['insels'].selectors
                comma = COMMA(self.parser, ',\n')
        elif self.insels :
            self.selectors = insels()

        # Call `this` ruleset's children in the context of its selectors
        if self.selectors :
            nestedtbl['insels'] = self.selectors()
            nestedtbl['insels'].parent = None
        self.block.nestedrulesets( igen, table )
        nestedtbl['insels'] = insels

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'ruleset: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Selectors( NonTerminal ):
    """class to handle `selectors` grammar."""

    flattenrule = ('selectors', ('selector', 'COMMA'))
    rhs = ('selectors', 'COMMA', 'selector')

    def __init__( self, parser, selectors, comma, selector ) :
        NonTerminal.__init__( self, parser, selectors, comma, selector )
        self._terms = (self.COMMA,) = (comma,)
        self._terms = filter( None, self._terms )
        self._nonterms = self.selectors, self.selector = selectors, selector
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None,  (self.selectors, self.COMMA, self.selector) )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        [ x.show(buf, offset, attrnames, showcoord) for x in self.safedesc() ]


class Selector( NonTerminal ):
    """class to handle `selector` grammar."""

    rhs = ('selector', 'COMBINATOR', 'simple_selector')

    def __init__( self, parser, selector, combinator, simplesel ) :
        NonTerminal.__init__( self, parser, selector, combinator, simplesel )
        self._terms = (self.COMBINATOR,) = (combinator,)
        self._terms = filter( None, self._terms )
        self._nonterms = self.selector,self.simple_selector = selector,simplesel
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def cdi( self, compsel, origsel, inssel, fromsel ):
        """Compare, Delete and Insert for @extend-ed selectors."""
        if (self.simple_selector, self.COMBINATOR) == (None, None) :
            # Passive fall through
            return self.selector.cdi( compsel, origsel, inssel, fromsel ) \
                   if self.selector else False
        ok = False
        if self.simple_selector :
            ok = self.simple_selector.compare( sel.simple_selector ) == True
        if self.COMBINATOR :
            ok = ok and (self.COMBINATOR.compare( sel.COMBINATOR ) == True)

        if ok and self.selector and csel.selector :     # Continue matching
            ok = self.selector.cdi( csel.selector, orisel, inssel, fromsel )
        elif ok and csel.selector == None :             # Full match
            if csel == osel :
                self.COMBINATOR, self.simple_selector = isel.COMBINATOR, isel.simple_selector
                self.setparent( self, self.children() )
                self.insertsubtree( isel.selector )
            else :
                self.delete('selector')
            ok = True
        elif self.selector :                            # Restart matching
            fromsel = self
            ok = self.selector.cdi( origsel, origsel, inssel, fromsel )
        else :                                          # Fail match
            ok = False
        return ok

    def children( self ):
        x = (self.selector, self.COMBINATOR, self.simple_selector)
        return filter( None, x )

    def nestedrulesets( self, igen, table ):
        if not table['nestedrules']['insels'] : return
        
        insel = table['nestedrules']['insels'].selector
        if self.simple_selector.isampersand() :         # Found parent reference
            self.insertsubtree( insel, 'selector' )
            self.simple_selector = None
        elif self.selector :                            # Continue
            self.selector.nestedrulesets( igen, table )
        else :                                          # Tail insert
            self.tailinsert( insel, 'selector' )
            self.COMBINATOR = COMBINATOR(self.parser, ' ')

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'selector: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class SimpleSelector( NonTerminal ):
    """class to handle `simple_selector` grammar."""

    rhs = ('SOLO', 'DOT', 'ident', 'hashh', 'attrib', 'pseudo')

    def __init__( self, parser, solo, dot, ident, hashh, attrib, pseudo ):
        NonTerminal.__init__(self, parser, solo, dot, ident, hashh, attrib, pseudo)
        self._terms = self.SOLO, self.DOT = solo, dot
        self._terms = filter( None, self._terms )
        self._nonterms = self.ident, self.hashh, self.attrib, self.pseudo = \
                ident, hashh, attrib, pseudo
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def isampersand( self ):
        return isinstance( self.SOLO, AMPERSAND )

    def children( self ):
        x = self.SOLO, self.DOT, self.ident, self.hashh, self.attrib, self.pseudo
        return filter( None, x )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'simple_selector: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Attrib( NonTerminal ) :
    """class to handle `attrib` grammar."""

    rhs = ('opensqr', 'left', 'operator', 'right', 'closesqr')

    def __init__( self, parser, osqr, left, oper, right, csqr ) :
        NonTerminal.__init__( self, parser, osqr, left, oper, right, csqr )
        self._nonterms = \
            self.opensqr, self.left, self.operator, self.right, self.closesqr =\
                osqr, left, oper, right, csqr
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = self.opensqr, self.left, self.operator, self.right, self.closesqr
        return filter(None, x)

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'attrib: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class AttrOperator( NonTerminal ):
    """class to handle `class` grammar."""

    rhs = ('TERMINAL',)

    def __init__( self, parser, term ) :
        NonTerminal.__init__( self, parser, term )
        self._terms = (self.TERMINAL,) = (term,)
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self._terms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'attroperator: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Pseudo( NonTerminal ):
    """class to handle `pseudo` grammar."""

    rhs = ('COLON1', 'COLON2', 'nonterm')

    def __init__( self, parser, colon1, colon2, nonterm ) :
        NonTerminal.__init__( self, parser, colon1, colon2, nonterm )
        self._terms = self.COLON1, self.COLON2 = colon1, colon2
        self._terms = filter( None, self._terms )
        self._nonterms = (self.nonterm,) = (nonterm,)
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.COLON1, self.COLON2, self.nonterm) )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'pseudo: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- Declaration block

class Block( NonTerminal ):
    """class to handle `block` grammar."""

    rhs = ('openbrace', 'declarations', 'closebrace')

    def __init__( self, parser, obrace, declarations, cbrace ) :
        NonTerminal.__init__( self, parser, obrace, declarations, cbrace )
        self._nonterms = \
            self.openbrace, self.declarations, self.closebrace = \
                obrace, declarations, cbrace
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self._nonterms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'block: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Declarations( NonTerminal ):
    """class to handle `declarations` grammar."""

    flattenrule = ( 'declarations', ('nonterm', 'wc', 'SEMICOLON'))
    rhs = ('declarations', 'SEMICOLON', 'wc', 'nonterm')

    def __init__( self, parser, declarations, semi, wc, nonterm ) :
        NonTerminal.__init__( self, parser, declarations, semi, wc, nonterm )
        self._terms = (self.SEMICOLON,) = (semi,)
        self._terms = filter( None, self._terms )
        self._nonterms = \
            self.declarations, self.wc, self.nonterm = declarations, wc, nonterm
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = self.declarations, self.SEMICOLON, self.wc, self.nonterm
        return filter( None, x )

    def validate( self, table ):
        if self.matchup((Page,)) :
            if self.matchdown((Page,)) :
                raise Exception('`@page` rule cannot be nested')
        else :
            if self.matchdown((PageMargin,)) :
                raise Exception('`pagemargin` found within non page directive')
        return all([ x.validate(table) for x in self.safedesc() ])

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        [ x.show(buf, offset, attrnames, showcoord) for x in self.safedesc() ]


class Declaration( NonTerminal ):
    """class to handle `declaration` grammar."""
    
    rhs = ('PREFIX', 'ident', 'COLON', 'exprs', 'prio')

    def __init__( self, parser, prefix, ident, colon, exprs, prio ) :
        NonTerminal.__init__(self, parser, prefix, ident, colon, exprs, prio)
        self._terms = self.PREFIX, self.COLON, = prefix, colon
        self._terms = filter( None, self._terms )
        self._nonterms = self.ident, self.exprs, self.prio = ident, exprs, prio
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = ( self.PREFIX, self.ident, self.COLON, self.exprs, self.prio )
        return filter(None, x)

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'declaration: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Priority( NonTerminal ):
    """class to handle `prio` grammar."""

    rhs = ('IMPORTANT_SYM', 'wc')

    def __init__( self, parser, sym, wc ) :
        NonTerminal.__init__( self, parser, sym )
        self._terms = (self.IMPORTANT_SYM,) = (sym,)
        self._nonterms = (self.wc,) = (wc,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self._terms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'prio: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


#---- Expressions

class TerminalS( NonTerminal ):
    """Base class for all `term` terms. Implements `term` grammar rule"""

    rhs = ('TERMINAL', 'wc')

    def __init__( self, parser, terminal, wc ) :
        NonTerminal.__init__( self, parser, terminal, wc )
        self._terms = (self.TERMINAL,) = (terminal,)
        self._nonterms = (self.wc,) = (wc,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !! 
        self.setparent( self, self.children() )

    def children( self ):
        return self._terms + self._nonterms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'TerminalS: %s' % self.TERMINAL.__class__ )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Exprs( NonTerminal ):
    """class to handle `exprs` grammar."""

    flattenrule = ('exprs', ('expr', 'COMMA'))
    rhs = ('exprs', 'COMMA', 'expr')

    def __init__( self, parser, exprs, comma, expr ):
        NonTerminal.__init__( self, parser, exprs, comma, expr )
        self._terms = (self.COMMA,) = (comma,)
        self._nonterms = self.exprs, self.expr = exprs, expr
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.exprs, self.COMMA, self.expr) )

    def generate( self, igen, table ):
        self.exprs and self.exprs.generate( igen, table )
        self.COMMA and self.COMMA.generate( igen, table )
        self.expr and self.expr.generate( igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'exprs: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


# Gotcha : There is a possibility of deep recursion here, although for
# practical inputs, it may not happen.

class Expr( NonTerminal ):
    """class to handle `expr` grammar."""

    rhs = ('term', 'spec', 'expr1', 'OPERATOR', 'expr2')

    def __init__( self, parser, term, spec, expr1, operator, expr2 ):
        NonTerminal.__init__(self, parser, term, spec, expr1, operator, expr2)
        self._terms = (self.OPERATOR,) = (operator,)
        self._terms = filter( None, self._terms )
        self._nonterms = self.term, self.spec, self.expr1, self.expr2 = \
                term, spec, expr1, expr2
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    # CSS standard allows / to appear in property values as a way of 
    # separating numbers and this leads to ambiguity with division operation
    # between numbers. To avoid this ambiguity the following situations
    # will be interpreted as division operation.

    # <Checks of expression begins here>

    def is_macroexpr( self ):
        return isinstance( self.spec, (ExprParan, ExprTernary) )

    # </Checks of expression ends here>

    def children( self ):
        x = self.term, self.spec, self.expr1, self.OPERATOR, self.expr2
        return filter( None, x )

    def generate( self, igen, table ):
        expreval = table['expreval']
        table['expreval'] = self.is_macroexpr() if not expreval else expreval
        NonTerminal.generate( self, igen, table )
        if table['expreval'] :
            if (self.expr1==None) and isinstance(self.OPERATOR, (PLUS,MINUS)):
                igen.evalunary()
            elif isinstance( self.OPERATOR, (PLUS, MINUS, STAR, FWDSLASH) ) :
                igen.evalbinary()
        table['expreval'] = expreval

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'expr: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class ExprParan( NonTerminal ):
    """class to handle `( expr )` grammar."""

    rhs = ('openparan', 'expr', 'closeparan')

    def __init__( self, parser, oparan, expr, cparan ) :
        NonTerminal.__init__( self, parser, oparan, expr, cparan )
        self._nonterms = self.openparan, self.expr, self.closeparan = \
                oparan, expr, cparan
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self._nonterms

    def generate( self, igen, table ):
        if filter( None, self.matchup((Declaration,)) ) :
            self.expr.generate( igen, table )
        else :
            NonTerminal.generate( self, igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'expr-paran: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class ExprTernary( NonTerminal ):
    """class to handle `expr QMARK expr COLON expr` grammar."""

    rhs = ('predicate', 'QMARK', 'exprcolon')

    def __init__( self, parser, pred, qmark, exprcolon ) :
        NonTerminal.__init__( self, parser, pred, qmark, exprcolon )
        self._terms = (self.QMARK,) = (qmark,)
        self._nonterms = self.predicate, self.exprcolon = pred, exprcolon
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self.predicate, self.QMARK, self.exprcolon

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'expr-ternary: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Term( NonTerminal ):
    """class to handle `term` grammar."""

    rhs = ('nonterm',)

    def __init__( self, parser, nonterm  ) :
        NonTerminal.__init__( self, parser, nonterm )
        self._nonterms = (self.nonterm,) = (nonterm,)
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        return self._nonterms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'term: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Dimension( TerminalS ):
    def generate( self, igen, table ): # Skip `wc` grammar.
        if table['expreval'] :
            self.TERMINAL.generate( igen, table ) 
        else :
            TerminalS.generate( self, igen, table )

class Number( TerminalS ):
    def generate( self, igen, table ): # Skip `wc` grammar.
        if table['expreval'] :
            self.TERMINAL.generate( igen, table ) 
        else :
            TerminalS.generate( self, igen, table )
        
class String( TerminalS ):
    def generate( self, igen, table ): # Skip `wc` grammar.
        if table['expreval'] :
            self.TERMINAL.generate( igen, table )
        else :
            TerminalS.generate( self, igen, table )


# Gotcha : This node can make an indirect recursive call to expr, hence end up
# in deep recursion

class FuncCall( NonTerminal ):
    """class to handle `func_call` grammar."""

    rhs = ('FUNCTION', 'exprs', 'simple_selector', 'closeparan')

    def __init__( self, parser, fun, exprs, simpsel, cparan ) :
        NonTerminal.__init__( self, parser, fun, exprs, simpsel, cparan )
        self._terms = (self.FUNCTION,) = (fun,)
        self._nonterms = \
            self.exprs, self.simple_selector, self.closeparan = \
                exprs, simpsel, cparan
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !!
        self.setparent( self, self.children() )

    def children( self ):
        x = self.FUNCTION, self.exprs, self.simple_selector, self.closeparan
        return filter( None, x )

    def generate( self, igen, table ):
        fnname = self.FUNCTION.dump(table)
        if (not self.simple_selector) and fnname.startswith('tss') :
            igen.evalfun( self.dump(table) )
        else :
            NonTerminal.generate( self, igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'func_call: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class CharsetSym( TerminalS ) : pass

class Ident( TerminalS ): pass
class Uri( TerminalS ): pass
class UnicodeRange( TerminalS ): pass
class Hash( TerminalS ): pass


class WC( NonTerminal ):
    """class to handle `wc` grammar."""

    flattenrule = ('wc', ('S', 'COMMENT'))
    rhs = ('wc', 'S', 'COMMENT')

    def __init__( self, parser, wc, s, comment ) :
        NonTerminal.__init__( self, parser, wc, s, comment )
        self._terms = self.S, self.COMMENT = s, comment
        self._terms = filter( None, self._terms )
        self._nonterms = (self.wc,) = (wc,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !! 
        self.setparent( self, self.children() )

    def children( self ):
        return self._nonterms + self._terms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        [ x.show(buf, offset, attrnames, showcoord) for x in self.safedesc() ]


class Any( NonTerminal ):
    """class to handle `any` grammar."""

    rhs = ('opensqr', 'expr', 'closesqr')

    def __init__( self, parser, osqr, expr, csqr ) :
        NonTerminal.__init__( self, parser, osqr, expr, csqr )
        self._nonterms = self.opensqr, self.expr, self.closesqr = osqr,expr,csqr
        # Set parent attribute for children, should be last statement !! 
        self.setparent( self, self.children() )

    def children( self ):
        return self._nonterms

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        [ x.show(buf, offset, attrnames, showcoord) for x in self.safedesc() ]


#---- Extension language

class ExtnExpr( NonTerminal ):
    """Wrapper for EXTN_EXPR terminal"""
    FILTER_DELIMITER = '|'

    rhs = ('EXTN_EXPR', 'wc') 

    def __init__( self, parser, extn_expr, wc ) :
        NonTerminal.__init__( self, parser, extn_expr, wc )
        self._terms = (self.EXTN_EXPR,) = (extn_expr,)
        self._nonterms = (self.wc,) = (wc,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !! 
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.EXTN_EXPR, self.wc) )

    def generate( self, igen, table ):
        from tss    import ESCFILTER_RE
        text = self.dump( table )
        code, filters = ExtnExpr.parseexprs( text )
        # Pre-process escape filters
        filters = ESCFILTER_RE.findall( filters.strip() + ',' )
        filters = [] if filters and filters[0][0] == 'n' else filters
        filters = [ ( f[0], f[1].strip('. ,') ) for f in filters if f ]
        igen.evalexprs( code, filters=filters )
        self.wc and self.wc.generate( igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'extn_expr: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]

    @classmethod
    def parseexprs( cls, text ):
        try    : text, filters = text.rsplit( cls.FILTER_DELIMITER, 1 )
        except : text, filters = text, u''
        return text, filters


class ExtnVar( NonTerminal ):
    """Wrapper for EXTN_VAR terminal"""

    rhs = ('EXTN_VAR', 'wc')

    def __init__( self, parser, extn_var, wc ) :
        NonTerminal.__init__( self, parser, extn_var, wc )
        self._terms = (self.EXTN_VAR,) = (extn_var,)
        self._nonterms = (self.wc,) = (wc,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !! 
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.EXTN_VAR, self.wc) )

    def generate( self, igen, table ):
        var = self.EXTN_VAR.dump(table)
        igen.pushobj( var )
        self.wc and self.wc.generate( igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'extn_var: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class ExtnStatement( NonTerminal ):
    """Wrapper for EXTN_STATEMENT terminal"""

    rhs = ('EXTN_STATEMENT', 'wc')

    def __init__( self, parser, extn_stmt, wc ) :
        NonTerminal.__init__( self, parser, extn_stmt, wc )
        self._terms = (self.EXTN_STATEMENT,) = (extn_stmt,)
        self._nonterms = (self.wc,) = (wc,)
        self._nonterms = filter( None, self._nonterms )
        # Set parent attribute for children, should be last statement !! 
        self.setparent( self, self.children() )

    def children( self ):
        return filter( None, (self.EXTN_STATEMENT, self.wc) )

    def defaultvar( self, stmt, var=u'' ):
        stmt = stmt.rstrip(' \t;')
        if stmt.endswith( '!default' ) :
            try : var = stmt.lstrip('$').split( '=', 1 )[0].strip()
            except : var = u''
            stmt = stmt[:-8]
        stmt = stmt[1:]
        return stmt, var

    def generate( self, igen, table ):
        stmt = self.EXTN_STATEMENT.dump(table)
        stmt, var = self.defaultvar( stmt )
        var and igen.putstatement( 'if locals().has_key( %r ) :' % var )
        var and igen.upindent(u'  ')
        igen.putstatement( stmt )
        var and igen.downindent(u'  ')
        self.wc and self.wc.generate( igen, table )

    def show(self, buf=sys.stdout, offset=0, attrnames=False, showcoord=False):
        lead = ' ' * offset
        buf.write( lead + 'extn_var: ' )
        if showcoord:
            buf.write( ' (at %s)' % self.coord )
        buf.write('\n')
        [ x.show(buf, offset+2, attrnames, showcoord) for x in self.safedesc() ]


class Openbrace( TerminalS ): pass
class Closebrace( TerminalS ): pass
class Opensqr( TerminalS ): pass
class Closesqr( TerminalS ): pass
class Openparan( TerminalS ): pass
class Closeparan( TerminalS ): pass
class Cdo( TerminalS ): pass
class Cdc( TerminalS ): pass

#-------------------------- AST Terminals -------------------------

class IMPORT_SYM( Terminal ) : pass
class PAGE_SYM( Terminal ) : pass
class PAGE_MARGIN_SYM( Terminal ) : pass
class MEDIA_SYM( Terminal ) : pass
class FONT_FACE_SYM( Terminal ) : pass
class CHARSET_SYM( Terminal ) : pass
class NAMESPACE_SYM( Terminal ) : pass
class IMPORTANT_SYM( Terminal ) : pass
class ATKEYWORD( Terminal ) : pass

class CDO( Terminal ) : pass
class CDATATEXT( Terminal ) : pass
class CDC( Terminal ) : pass
class S( Terminal ) : pass
class COMMENT( Terminal ) : pass

class IDENT( Terminal ) : pass
class URI( Terminal ) : pass
class FUNCTION( Terminal ) : pass
class FUNTEXT( Terminal ) : pass
class FUNCLOSE( Terminal ) : pass

class HASH( Terminal ) : pass
class INCLUDES( Terminal ) : pass
class DASHMATCH( Terminal ) : pass
class PREFIXMATCH( Terminal ) : pass
class SUFFIXMATCH( Terminal ) : pass
class SUBSTRINGMATCH( Terminal ) : pass

class PERCENTAGE( Terminal ) : pass

class UNICODERANGE( Terminal ) : pass
class AMPERSAND( Terminal ) : pass

class PLUS( Terminal ) : pass
class MINUS( Terminal ) : pass
class GT( Terminal ) : pass
class LT( Terminal ) : pass
class TILDA( Terminal ) : pass
class COMMA( Terminal ) : pass
class COLON( Terminal ) : pass
class EQUAL( Terminal ) : pass
class DOT( Terminal ) : pass
class STAR( Terminal ) : pass
class PREFIXSTAR( Terminal ) : pass
class SEMICOLON( Terminal ) : pass
class FWDSLASH( Terminal ) : pass
class AND( Terminal ) : pass
class OR( Terminal ) : pass
class QMARK( Terminal ) : pass
class OPENBRACE( Terminal ) : pass
class CLOSEBRACE( Terminal ) : pass
class OPENSQR( Terminal ) : pass
class CLOSESQR( Terminal ) : pass
class OPENPARAN( Terminal ) : pass
class CLOSEPARAN( Terminal ) : pass

class EXTN_EXPR( Terminal ) : pass
class EXTN_VAR( Terminal ) : pass
class EXTN_STATEMENT( Terminal ) : pass
class PERCENT( Terminal ) : pass
class FUNCTIONSTART( Terminal ) : pass
class FUNCTIONBODY( Terminal ) : pass
class IFCONTROL( Terminal ) : pass
class ELIFCONTROL( Terminal ) : pass
class ELSECONTROL( Terminal ) : pass
class FORCONTROL( Terminal ) : pass
class WHILECONTROL( Terminal ) : pass

# TODO : Why are these terminal here ?
class HEXCOLOR( Terminal ) : pass
class NAME( Terminal ) : pass
class FUNCTIONEND( Terminal ) : pass

#---- Terminals abstracted as DIMENSION
class DIMENSION( Terminal ):
    def generate( self, igen, table ):
        igen.pushobj( self.emit( igen, table ))

    def emit( self, igen, table ):
        return u'%s_( %r )' % (self.__class__.__name__, self.terminal)

class EMS( DIMENSION ): pass
class EXS( DIMENSION ): pass
class LENGTHPX( DIMENSION ): pass
class LENGTHCM( DIMENSION ): pass
class LENGTHMM( DIMENSION ): pass
class LENGTHIN( DIMENSION ): pass
class LENGTHPT( DIMENSION ): pass
class LENGTHPC( DIMENSION ): pass
class ANGLEDEG( DIMENSION ): pass
class ANGLERAD( DIMENSION ): pass
class ANGLEGRAD( DIMENSION ): pass
class TIMEMS( DIMENSION ): pass
class TIMES( DIMENSION ): pass
class FREQHZ( DIMENSION ): pass
class FREQKHZ( DIMENSION ): pass
class PERCENTAGE( DIMENSION ): pass

#---- Special Terminals

class NUMBER( Terminal ):
    def generate( self, igen, table ):
        igen.pushobj( self.emit( igen, table ))

    def emit( self, igen, table ):
        return u"%s_( %r )" % (self.__class__.__name__, self.terminal)

class STRING( Terminal ):
    def generate( self, igen, table ):
        igen.pushobj( self.emit( igen, table ))

    def emit( self, igen, table ):
        val = self.terminal.replace("'", "\\'")
        return u"%s_( u'%s' )" % ( self.__class__.__name__, val )

class HASH( Terminal ): pass
