# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Parser grammer for TSS Extension language"""

# Gotcha : None
# Notes  :
#   W3C reference :
#     * Grammar, http://www.w3.org/TR/css3-syntax/
#     * Selectors, http://www.w3.org/TR/selectors/
#     * @page syntax rule, http://www.w3.org/TR/css3-page/
# Todo   : 

import logging, sys, codecs
from   copy         import deepcopy
from   types        import StringType
from   os.path      import splitext, dirname
from   hashlib      import sha1

import ply.yacc
from   tss.lexer    import TSSLexer
from   tss.ast      import *
from   utils        import throw

log = logging.getLogger( __name__ )
rootdir = dirname( __file__ )
LEXTAB = 'lextsstab'
YACCTAB = 'parsetsstab'

class ParseError( Exception ):
    pass

# Default Wiki page properties
class TSSParser( object ):

    def __init__( self,
                  tssconfig={},
                  encoding=None,
                  outputdir='',
                  lex_debug=None,
                  yacc_debug=None,
                  debug=None
                ):
        """
        Create a new TSSParser.

        ``tssconfig``
            All configurations related to tayra templates, are represented in
            this object.

        ``encoding``
            Character encoding for input Tayra style text.

        ``outputdir``
            To change the directory in which the parsetab.py file (and other
            output files) are written.

        ``lex_debug``
            PLY-Yacc option.

        ``yacc_debug``
            Generate a parser.out file that explains how yacc built the parsing
            table from the grammar.
        """
        self.debug = lex_debug or yacc_debug or debug
        self.encoding = encoding
        optimize = tssconfig.get( 'parse_optimize', False )
        lextab = tssconfig.get( 'lextab', LEXTAB ) or LEXTAB
        yacctab = tssconfig.get( 'yacctab', YACCTAB ) or YACCTAB
        # Build Lexer
        self.tsslex = TSSLexer( error_func=self._lex_error_func )
        kwargs = { 'optimize' : optimize } if optimize else {}
        kwargs.update( debug=lex_debug )
        kwargs.update( lextab=lextab ) if lextab else None
        self.tsslex.build( **kwargs )
        self.tokens = self.tsslex.tokens
        # Build Yaccer
        kwargs = { 'optimize' : optimize } if optimize else {}
        kwargs.update( debug=(yacc_debug or debug) )
        kwargs.update( outputdir=outputdir ) if outputdir else None
        kwargs.update( tabmodule=yacctab )
        self.parser = ply.yacc.yacc( module=self, **kwargs )
        self.parser.tssparser = self        # For AST nodes to access `this`
        # Parser initialization
        self._tssconfig = tssconfig
        self._initialize()

    def _initialize( self, tssfile=None, tssconfig={} ):
        self.tssfile = tssfile
        self.tssconfig = deepcopy( self._tssconfig )
        self.tssconfig.update( tssconfig )
        self.tsslex.reset_lineno()

    def parse( self, text, tssfile=None, tssconfig={}, debuglevel=0 ):
        """Parse TSS and creates an AST tree. For every
        parsing invocation, the same lex, yacc, app options and objects will
        be used.

        ``filename``
            Name of the file being parsed (for meaningful error messages)
        ``debuglevel``
            Debug level to yacc
        """
        # Parser Initialize
        tssfile = tssfile if tssfile != None else self.tssfile
        self._initialize( tssfile=tssfile, tssconfig=tssconfig )
        self.tsslex.filename = self.tssfile = tssfile

        # parse and get the translation unit
        self.text = text

        # parse and get the Translation Unit
        debuglevel = self.debug or debuglevel
        tracking = True if self.debug or debuglevel else False
        self.tu = self.parser.parse(
            text, lexer=self.tsslex, debug=debuglevel, tracking=tracking )
        return self.tu

    # ------------------------- Private functions -----------------------------

    def _lex_error_func( self, lex, msg, line, column ):
        self._parse_error( msg, self._coord( line, column ))
    
    def _coord( self, lineno, column=None ):
        return Coord( file=self.tsslex.filename, line=lineno, column=column )
    
    def _parse_error(self, msg, coord):
        raise ParseError("%s: %s" % (coord, msg))

    def _printparse( self, p ):
        print p[0], "  : ",
        for i in range(1,len(p)) :
            print p[i],
        print

    def _termwspac2nonterm( self, p, text, termcls, nontermcls ):
        text1 = text.rstrip(' \t\r\n\f')
        term, wspac = text[:len(text1)], text[len(text1):]
        wc = WC( p.parser, None, S(p.parser, wspac), None )
        return nontermcls( termcls(p.parser, term), wc )

    # ---------- Precedence and associativity of operators --------------------

    precedence = (
        ('left', 'COMMA'),
        ('left', 'QMARK', 'COLON'),
        ('left', 'EQUAL'),
        ('left', 'GT', 'LT', 'AND', 'OR'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'STAR', 'FWDSLASH'),
        ('right', 'UNARY'),
    )

    def _buildterms( self, p, terms ):
        rc = []
        for t in terms :
            if t == None : 
                rc.append( None )
                continue
            elif isinstance(t, tuple) :
                cls, idx = t
                rc.append( cls(p.parser, p[idx]) )
            else :
                rc.append(t)
        return rc

    # TODO : Makes sure that charset, import and namespace non-terminals
    # does not follow rulesets, media, page, font_face non-terminals

    def p_tss( self, p ):
        """tss          : cdata
                        | charset
                        | namespace
                        | font_face
                        | page
                        | media
                        | atrule
                        | rulesets
                        | wc
                        | tss cdata
                        | tss charset
                        | tss namespace
                        | tss font_face
                        | tss page
                        | tss media
                        | tss atrule
                        | tss rulesets
                        | tss wc"""
        if len(p) == 3 :
            p[2] = Rulesets( p.parser, p[2], None )
            p[0] = Tss( p.parser, p[1], p[2] )
        else :
            p[1] = Rulesets( p.parser, p[1], None )
            p[0] = Tss( p.parser, None, p[1] )

    #---- CDATA

    def p_cdata_1( self, p ):
        """cdata        : CDO CDATATEXT CDC"""
        x = [ (CDO, 1), (CDATATEXT, 2), (CDC, 3) ]
        p[0] = Cdata( p.parser, *self._buildterms(p, x) )

    def p_cdata_2( self, p ):
        """cdata        : CDO CDC"""
        x = [ (CDO, 1), None, (CDC, 2) ]
        p[0] = Cdata( p.parser, *self._buildterms(p, x) )

    #---- @charset 

    def p_charset( self, p ):
        """charset      : CHARSET_SYM string SEMICOLON"""
        x = [ (CHARSET_SYM, 1), p[2], (SEMICOLON, 3) ]
        p[0] = Charset( p.parser, *self._buildterms(p, x) )

    #---- @namespace

    def p_namespace_1( self, p ):
        """namespacspec : NAMESPACE_SYM ident
                        | NAMESPACE_SYM EXTN_VAR"""
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        p[0] = [ NAMESPACE_SYM(p.parser, p[1]), p[2], None, None ]

    def p_namespace_2( self, p ):
        """namespacspec : NAMESPACE_SYM string
                        | NAMESPACE_SYM uri
                        | NAMESPACE_SYM EXTN_EXPR"""
        if not isinstance(p[2], (String, Uri)) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_EXPR, ExtnExpr )
        p[0] = [ NAMESPACE_SYM(p.parser, p[1]), None, p[2], None ]

    def p_namespace_3( self, p ):
        """namespacspec : namespacspec string
                        | namespacspec uri
                        | namespacspec EXTN_EXPR"""
        if p[1][2] :
            raise Exception( 'Multiple string or uri not allowed in namespace' )
        if not isinstance(p[2], (String, Uri)) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_EXPR, ExtnExpr )
        p[1][2] = p[2]
        p[0] = p[1]

    def p_namespace_4( self, p ):
        """namespace    : namespacspec SEMICOLON"""
        p[1][3] = SEMICOLON( p.parser, p[2] )
        p[0] = Namespace( p.parser, *p[1] )

    #---- @font_face

    def p_font_face( self, p ):
        """font_face    : FONT_FACE_SYM block"""
        x = [ (FONT_FACE_SYM, 1), p[2] ]
        p[0] = FontFace( p.parser, *self._buildterms(p, x) )

    #---- atrule

    # Gotcha : Handle generic at-rules
    def p_atrule_1( self, p ):
        """atrule       : ATKEYWORD expr block"""
        x = [ (ATKEYWORD, 1), p[2], p[3], None, None, ]
        p[0] = AtRule( p.parser, *self._buildterms(p, x) )

    def p_atrule_2( self, p ):
        """atrule       : ATKEYWORD expr SEMICOLON"""
        x = [ (ATKEYWORD, 1), p[2], None, (SEMICOLON, 3), None, ]
        p[0] = AtRule( p.parser, *self._buildterms(p, x) )

    def p_atrule_3( self, p ):
        """atrule       : ATKEYWORD block"""
        x = [ (ATKEYWORD, 1), None, p[2], None, None, ]
        p[0] = AtRule( p.parser, *self._buildterms(p, x) )

    def p_atrule_4( self, p ):
        """atrule       : ATKEYWORD SEMICOLON"""
        x = [ (ATKEYWORD, 1), None, None, (SEMICOLON, 2), None, ]
        p[0] = AtRule( p.parser, *self._buildterms(p, x) )

    def p_atrule_5( self, p ):
        """atrule       : ATKEYWORD expr openbrace rulesets closebrace"""
        term = ATKEYWORD(p.parser, p[1])
        p[4] = Rulesets(p.parser, p[4], None)
        p[0] = AtRule( p.parser, term, p[2], None, None, (p[3], p[4], p[5]) )

    def p_atrule_6( self, p ):
        """atrule       : ATKEYWORD openbrace rulesets closebrace"""
        term = ATKEYWORD(p.parser, p[1])
        p[3] = Rulesets(p.parser, p[3], None)
        p[0] = AtRule( p.parser, term, None, None, None, (p[2], p[3], p[4]) )

    #---- @media

    def p_media_1( self, p ):
        """mediaspec    : MEDIA_SYM IDENT
                        | MEDIA_SYM IDENT S """
        x = [ (IDENT, 2), (S, 3) ] if len(p)==4 else [ (IDENT, 2), None ]
        x = [ None, None ] + x
        meds = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = [ MEDIA_SYM(p.parser, p[1]), meds, None, None, None, None ]

    def p_media_2( self, p ):
        """mediaspec    : MEDIA_SYM EXTN_VAR"""
        p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        x = [ None, None, p[2], None ]
        meds = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = [ MEDIA_SYM(p.parser, p[1]), meds, None, None, None, None ]

    def p_media_3( self, p ):
        """mediaspec    : mediaspec COMMA IDENT
                        | mediaspec COMMA IDENT S"""
        cls, value = p[2]
        x = [ (IDENT, 3), (S, 4) ] if len(p)==5 else [ (IDENT, 3), None ]
        x = [ p[1][1], cls(p.parser, value) ] + x
        p[1][1] = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = p[1]

    def p_media_4( self, p ):
        """mediaspec    : mediaspec COMMA EXTN_VAR"""
        cls, value = p[2]
        p[3] = self._termwspac2nonterm( p, p[3], EXTN_VAR, ExtnVar )
        x = [ p[1][1], cls(p.parser, value), p[3], None ]
        p[1][1] = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = p[1]

    def p_media_5( self, p ):
        """media        : mediaspec exprs openbrace rulesets closebrace"""
        p[4] = Rulesets(p.parser, p[4], None)
        p[1][2], p[1][3], p[1][4], p[1][5] = p[2], p[3], p[4], p[5]
        p[0] = Media( p.parser, *p[1] )

    def p_media_6( self, p ):
        """media        : mediaspec exprs openbrace closebrace"""
        p[1][2], p[1][3], p[1][4], p[1][5] = p[2], p[3], None, p[4]
        p[0] = Media( p.parser, *p[1] )

    def p_media_7( self, p ):
        """media        : mediaspec openbrace rulesets closebrace"""
        p[3] = Rulesets(p.parser, p[3], None)
        p[1][2], p[1][3], p[1][4], p[1][5] = None, p[2], p[3], p[4]
        p[0] = Media( p.parser, *p[1] )

    def p_media_8( self, p ):
        """media        : mediaspec openbrace closebrace"""
        p[1][2], p[1][3], p[1][4], p[1][5] = None, p[2], None, p[3]
        p[0] = Media( p.parser, *p[1] )

    #---- @page

    def p_page_1( self, p ):
        """page         : PAGE_SYM ident block
                        | PAGE_SYM EXTN_VAR block"""
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        x = [ (PAGE_SYM, 1), p[2], None, None, p[3] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_page_2( self, p ):
        """page         : PAGE_SYM COLON ident block
                        | PAGE_SYM COLON EXTN_VAR block"""
        cls, val = p[2]
        if not isinstance(p[3], Ident) :
            p[3] = self._termwspac2nonterm( p, p[3], EXTN_VAR, ExtnVar )
        x = [ (PAGE_SYM, 1), None, cls(p.parser, val), p[3], p[4] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_page_3( self, p ):
        """page         : PAGE_SYM ident COLON ident block
                        | PAGE_SYM EXTN_VAR COLON ident block
                        | PAGE_SYM ident COLON EXTN_VAR block
                        | PAGE_SYM EXTN_VAR COLON EXTN_VAR block"""
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        cls, val = p[3]
        if not isinstance(p[4], Ident) :
            p[4] = self._termwspac2nonterm( p, p[4], EXTN_VAR, ExtnVar )
        x = [ (PAGE_SYM, 1), p[2], cls(p.parser, val), p[4], p[5] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_page_4( self, p ):
        """page         : PAGE_SYM block"""
        x = [ (PAGE_SYM, 1), None, None, None, p[2] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_pagemargin_1( self, p ):
        """pagemargin   : PAGE_MARGIN_SYM block"""
        term = PAGE_MARGIN_SYM(p.parser, p[1])
        p[0] = PageMargin( p.parser, term, p[2] )

    def p_pagemargin_2( self, p ):
        """pagemargin   : PAGE_MARGIN_SYM"""
        term = PAGE_MARGIN_SYM(p.parser, p[1])
        p[0] = PageMargin( p.parser, term, None )

    #---- @import

    def p_import_1( self, p ):
        """importspec   : IMPORT_SYM string
                        | IMPORT_SYM uri"""
        p[0] = [ IMPORT_SYM(p.parser, p[1]), p[2], None, None ]

    def p_import_2( self, p ):
        """importspec   : importspec IDENT
                        | importspec IDENT S"""
        x = [ (IDENT, 2), (S, 3) ] if len(p)==4 else [ (IDENT, 2), None ]
        x = [ p[1][2], None ] + x
        p[1][2] = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = p[1]

    def p_import_3( self, p ):
        """importspec   : importspec EXTN_VAR"""
        p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        x = [ p[1][2], None, p[2], None ]
        p[1][2] = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = p[1]

    def p_import_4( self, p ):
        """importspec   : importspec COMMA IDENT
                        | importspec COMMA IDENT S"""
        x = [ (IDENT, 3), (S, 4) ] if len(p)==5 else [ (IDENT, 3), None ]
        cls, value = p[2]
        x = [ p[1][2], cls(p.parser, value) ] + x
        p[1][2] = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = p[1]

    def p_import_5( self, p ):
        """importspec   : importspec COMMA EXTN_VAR"""
        cls, value = p[2]
        p[3] = self._termwspac2nonterm( p, p[3], EXTN_VAR, ExtnVar )
        x = [ p[1][2], cls(p.parser, value), p[3], None ]
        p[1][2] = Mediums( p.parser, *self._buildterms(p, x) )
        p[0] = p[1]

    def p_import_6( self, p ):
        """import       : importspec SEMICOLON"""
        p[1][3] = SEMICOLON( p.parser, p[2] )
        p[0] = Import( p.parser, *p[1] )

    #---- extend

    def p_extend_1( self, p ):
        """extend       : EXTEND_SYM selector SEMICOLON"""
        x = [ (EXTEND_SYM, 1), p[2], (SEMICOLON, 3), None ]
        p[0] = Extend( p.parser, *self._buildterms(p, x) ]
    
    def p_extend_2( self, p ):
        """extend       : EXTEND_SYM selector SEMICOLON wc"""
        x = [ (EXTEND_SYM, 1), p[2], (SEMICOLON, 3), p[4] ]
        p[0] = Extend( p.parser, *self._buildterms(p, x) ]
    
    #---- ruleset

    # TODO : only `&` is allowd in DLIMIT terminal, this constraint should
    # be checked inside `ElementName` class
    def p_rulesets_1( self, p ):
        """rulesets     : ruleset
                        | import
                        | rulesets ruleset
                        | rulesets import"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None, p[1] ]
        p[0] = Rulesets( p.parser, *args )

    def p_rulesets_2( self, p ):
        """rulesets     : EXTN_STATEMENT
                        | rulesets EXTN_STATEMENT"""
        if len(p) == 3 :
            p[1] = self._termwspac2nonterm(p, p[1], EXTN_STATEMENT, ExtnStatement)
            p[0] = Rulesets( p.parser, None, p[1] )
        else :
            p[2] = self._termwspac2nonterm(p, p[2], EXTN_STATEMENT, ExtnStatement)
            p[0] = Rulesets( p.parser, p[1], p[2] )

    def p_ruleset_1( self, p ):
        """ruleset      : block
                        | selectors block"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None, p[1] ]
        p[0] = Ruleset( p.parser, *args )

    def p_selectors_1( self, p ):
        """selectors    : selector"""
        x = [ None, None, p[1] ]
        p[0] = Selectors( p.parser, *self._buildterms(p, x) )

    def p_selectors_2( self, p ):
        """selectors    : selectors COMMA selector"""
        cls, val = p[2]
        x = [ p[1], cls(p.parser, val), p[3] ]
        p[0] = Selectors( p.parser, *self._buildterms(p, x) )

    def p_selector_1( self, p ):
        """selector     : simpselector
                        | EXTN_EXPR """
        if not isinstance(p[1], SimpleSelector) :
            p[1] = self._termwspac2nonterm( p, p[1], EXTN_EXPR, ExtnExpr )
        p[0] = Selector( p.parser, None, None, p[1] )

    def p_selector_2( self, p ):
        """selector     : selector simpselector"""
        p[0] = Selector( p.parser, p[1], None, p[2] )

    def p_selector_3( self, p ):
        """selector     : selector SEL_GT simpselector
                        | selector SEL_PLUS simpselector
                        | selector SEL_TILDA simpselector"""
        cls, value =p[2]
        p[0] = Selector( p.parser, p[1], cls(p.parser, value), p[3] )

    def p_simpselector_1( self, p ):
        """simpselector : sel_ident
                        | SEL_EXTN_VAR"""
        if not isinstance(p[1], Ident) :
            p[1] = self._termwspac2nonterm( p, p[1], EXTN_VAR, ExtnVar )
        p[0] = SimpleSelector( p.parser, None, None, p[1], None, None, None )

    def p_simpselector_2( self, p ):
        """simpselector : sel_hash"""
        p[0] = SimpleSelector( p.parser, None, None, None, p[1], None, None )

    def p_simpselector_3( self, p ):
        """simpselector : SEL_STAR
                        | AMPERSAND"""
        cls, value = p[1]
        term = cls(p.parser, value)
        p[0] = SimpleSelector( p.parser, term, None, None, None, None, None )

    def p_simpselector_4( self, p ):
        """simpselector : DOT sel_ident
                        | DOT EXTN_VAR"""
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        cls, value = p[1]
        term = cls(p.parser, value)
        p[0] = SimpleSelector( p.parser, None, term, p[2], None, None, None )

    def p_simpselector_5( self, p ):
        """simpselector : attrib"""
        p[0] = SimpleSelector( p.parser, None, None, None, None, p[1], None )

    def p_simpselector_6( self, p ):
        """simpselector : pseudo"""
        p[0] = SimpleSelector( p.parser, None, None, None, None, None, p[1] )

    def p_attrib_1( self, p ):
        """attrib       : opensqr sel_ident attroperator sel_ident closesqr
                        | opensqr sel_ident attroperator sel_string closesqr"""
        p[0] = Attrib( p.parser, p[1], p[2], p[3], p[4], p[5] )

    def p_attrib_2( self, p ):
        """attrib       : opensqr EXTN_VAR attroperator sel_ident closesqr
                        | opensqr EXTN_VAR attroperator sel_string closesqr"""
        p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        p[0] = Attrib( p.parser, p[1], p[2], p[3], p[4], p[5] )

    def p_attrib_3( self, p ):
        """attrib       : opensqr sel_ident attroperator EXTN_VAR closesqr"""
        p[4] = self._termwspac2nonterm( p, p[4], EXTN_VAR, ExtnVar )
        p[0] = Attrib( p.parser, p[1], p[2], p[3], p[4], p[5] )

    def p_attrib_4( self, p ):
        """attrib       : opensqr sel_ident attroperator EXTN_EXPR closesqr"""
        p[4] = self._termwspac2nonterm( p, p[4], EXTN_EXPR, ExtnExpr )
        p[0] = Attrib( p.parser, p[1], p[2], p[3], p[4], p[5] )

    def p_attrib_5( self, p ):
        """attrib       : opensqr sel_ident closesqr
                        | opensqr EXTN_VAR closesqr"""
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        p[0] = Attrib( p.parser, p[1], p[2], None, None, p[3] )

    def p_attroperator( self, p ):
        """attroperator : SEL_EQUAL
                        | INCLUDES
                        | DASHMATCH
                        | PREFIXMATCH
                        | SUFFIXMATCH
                        | SUBSTRINGMATCH"""
        cls, value = p[1]
        p[0] = AttrOperator( p.parser, cls(p.parser, value) )

    def p_pseudo_1( self, p ):
        """pseudo       : SEL_COLON sel_ident
                        | SEL_COLON func_call"""
        cls, value = p[1]
        p[0] = Pseudo( p.parser, None, cls(p.parser, value), p[2] )

    def p_pseudo_2( self, p ):
        """pseudo       : SEL_COLON EXTN_VAR"""
        cls, value = p[1]
        p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        p[0] = Pseudo( p.parser, None, cls(p.parser, value), p[2] )

    def p_pseudo_3( self, p ):
        """pseudo       : SEL_COLON SEL_COLON sel_ident
                        | SEL_COLON SEL_COLON func_call"""
        cls1, val1 = p[1]
        cls2, val2 = p[2]
        p[0] = Pseudo( p.parser, cls1(p.parser,val1), cls2(p.parser,val2), p[3] )

    def p_pseudo_4( self, p ):
        """pseudo       : SEL_COLON SEL_COLON EXTN_VAR"""
        cls1, val1 = p[1]
        cls2, val2 = p[2]
        p[3] = self._termwspac2nonterm( p, p[3], EXTN_VAR, ExtnVar )
        p[0] = Pseudo( p.parser, cls1(p.parser,val1), cls2(p.parser,val2), p[3] )

    #---- Declaration block

    def p_block( self, p ):
        """block        : openbrace declarations closebrace
                        | openbrace closebrace"""
        args = [ p[1], p[2], p[3] ] if len(p) == 4 else [ p[1], None, p[2] ]
        p[0] = Block( p.parser, *args )

    def p_declarations_1( self, p ):
        """declarations : extend
                        | declaration
                        | pagemargin
                        | rulesets"""
        p[1] = Rulesets(p.parser, p[1], None)
        p[0] = Declarations( p.parser, None, None, None, p[1] )

    def p_declarations_3( self, p ):
        """declarations : pagemargin declaration
                        | rulesets declaration"""
        p[1] = Rulesets(p.parser, p[1], None)
        dcls = Declarations( p.parser, None, None, None, p[1] )
        p[0] = Declarations( p.parser, dcls, None, None, p[2] )

    def p_declarations_4( self, p ):
        """declarations : declarations SEMICOLON"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, None, None )

    def p_declarations_5( self, p ):
        """declarations : declarations SEMICOLON declaration"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, None, p[3] )

    def p_declarations_6( self, p ):
        """declarations : declarations SEMICOLON wc"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, p[3], None )

    def p_declarations_7( self, p ):
        """declarations : declarations SEMICOLON wc declaration"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, p[3], p[4] )

    def p_declarations_8( self, p ):
        """declarations : declarations rulesets
                        | declarations pagemargin"""
        p[2] = Rulesets(p.parser, p[2], None)
        p[0] = Declarations( p.parser, p[1], None, None, p[2] )

    def p_declarations_9( self, p ):
        """declarations : declarations pagemargin declaration
                        | declarations rulesets declaration"""
        p[2] = Rulesets(p.parser, p[2], None)
        dcls = Declarations( p.parser, p[1], None, None, p[2] )
        p[0] = Declarations( p.parser, dcls, None, None, p[3] )

    def p_declaration_1( self, p ):
        """declaration  : ident COLON exprs
                        | ident COLON EXTN_EXPR
                        | EXTN_VAR COLON exprs
                        | EXTN_VAR COLON EXTN_EXPR"""
        if not isinstance(p[1], Ident) :
            p[1] = self._termwspac2nonterm( p, p[1], EXTN_VAR, ExtnVar )
        cls, value = p[2]
        if not isinstance(p[3], Exprs) :
            p[3] = self._termwspac2nonterm( p, p[3], EXTN_EXPR, ExtnExpr )
        x = [ None, p[1], cls(p.parser, value), p[3], None ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_declaration_2( self, p ):
        """declaration  : ident COLON exprs prio
                        | ident COLON EXTN_EXPR prio
                        | EXTN_VAR COLON exprs prio
                        | EXTN_VAR COLON EXTN_EXPR prio"""
        if not isinstance(p[1], Ident) :
            p[1] = self._termwspac2nonterm( p, p[1], EXTN_VAR, ExtnVar )
        cls, value = p[2]
        if not isinstance(p[3], Exprs) :
            p[3] = self._termwspac2nonterm( p, p[3], EXTN_EXPR, ExtnExpr )
        x = [ None, p[1], cls(p.parser, value), p[3], p[4] ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_declaration_3( self, p ):
        """declaration  : PREFIXSTAR ident COLON exprs
                        | PREFIXSTAR ident COLON EXTN_EXPR
                        | PREFIXSTAR EXTN_VAR COLON exprs
                        | PREFIXSTAR EXTN_VAR COLON EXTN_EXPR"""
        cls1, val1 = p[1]
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        cls2, val2 = p[3]
        if not isinstance(p[4], Exprs) :
            p[4] = self._termwspac2nonterm( p, p[4], EXTN_EXPR, ExtnExpr )
        x = [ cls1(p.parser, val1), p[2], cls2(p.parser, val2), p[4], None ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_declaration_4( self, p ):
        """declaration  : PREFIXSTAR ident COLON exprs prio
                        | PREFIXSTAR ident COLON EXTN_EXPR prio
                        | PREFIXSTAR EXTN_VAR COLON exprs prio
                        | PREFIXSTAR EXTN_VAR COLON EXTN_EXPR prio"""
        cls1, val1 = p[1]
        if not isinstance(p[2], Ident) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_VAR, ExtnVar )
        cls2, val2 = p[3]
        if not isinstance(p[4], Exprs) :
            p[3] = self._termwspac2nonterm( p, p[3], EXTN_EXPR, ExtnExpr )
        x = [ cls1(p.parser, val1), p[2], cls2(p.parser, val2), p[4], p[5] ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_prio( self, p ):
        """prio         : IMPORTANT_SYM
                        | IMPORTANT_SYM wc"""
        x = [ (IMPORTANT_SYM, 1), p[2]
            ] if len(p)==3 else [ (IMPORTANT_SYM, 1), None ]
        p[0] = Priority( p.parser, *self._buildterms(p, x) )

    #---- expressions

    def p_exprs_1( self, p ):
        """exprs        : expr"""
        p[0] = Exprs( p.parser, None, None, p[1] )

    def p_exprs_2( self, p ):
        """exprs        : exprs expr"""
        p[0] = Exprs( p.parser, p[1], None, p[2] )

    def p_exprs_3( self, p ):
        """exprs        : exprs COMMA expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Exprs( p.parser, p[1], term, p[3] )

    def p_expr_1( self, p ):
        """expr         : term"""
        args = [ p[1], None, None, None, None ]
        p[0] = Expr( p.parser, *args )

    def p_expr_2( self, p ):
        """expr         : openparan expr closeparan
                        | openparan exprcolon closeparan"""
        expr = ExprParan( p.parser, p[1], p[2], p[3] )
        p[0] = Expr( p.parser, None, expr, None, None, None )

    def p_expr_3( self, p ):
        """expr         : expr QMARK exprcolon"""
        cls, value = p[2]
        term = cls(p.parser, value)
        expr = ExprTernary( p.parser, p[1], term, p[3] )
        p[0] = Expr( p.parser, None, expr, None, None, None )

    def p_expr_4( self, p ):
        """expr         : expr PLUS expr
                        | expr MINUS expr
                        | expr STAR expr
                        | expr AND expr
                        | expr OR expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, p[1], term, p[3] )

    def p_expr_5( self, p ):
        """expr         : expr FWDSLASH expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, p[1], term, p[3] )

    def p_expr_6( self, p ):
        """expr         : expr EQUAL expr
                        | expr GT expr
                        | expr LT expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, p[1], term, p[3] )

    def p_expr_7( self, p ):
        """expr         : MINUS expr %prec UNARY
                        | PLUS expr %prec UNARY"""
        cls, value = p[1]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, None, term, p[2] )

    def p_exprcolon( self, p ):
        """exprcolon    : expr COLON expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, p[1], term, p[3] )

    def p_term_1( self, p ):
        """term         : number
                        | dimension
                        | func_call
                        | ident
                        | string
                        | uri
                        | unicoderange
                        | hash
                        | EXTN_VAR"""
        ts = (Number, Dimension, FuncCall, Ident, String, Uri, UnicodeRange, Hash)
        if not isinstance(p[1], ts) :
            p[1] = self._termwspac2nonterm( p, p[1], EXTN_VAR, ExtnVar )
        p[0] = Term( p.parser, p[1] )

    def p_func_call_1( self, p ):
        """func_call    : FUNCTION exprs closeparan
                        | FUNCTION EXTN_EXPR closeparan"""
        if not isinstance(p[2], Exprs) :
            p[2] = self._termwspac2nonterm( p, p[2], EXTN_EXPR, ExtnExpr )
        x = [ (FUNCTION, 1), p[2], None, p[3] ]
        p[0] = FuncCall( p.parser, *self._buildterms(p, x) )

    def p_func_call_2( self, p ):
        """func_call    : FUNCTION simpselector closeparan"""
        x = [ (FUNCTION, 1), None, p[2], p[3] ]
        p[0] = FuncCall( p.parser, *self._buildterms(p, x) )

    def p_func_call_3( self, p ):
        """func_call    : FUNCTION closeparan"""
        x = [ (FUNCTION, 1), None, None, p[2] ]
        p[0] = FuncCall( p.parser, *self._buildterms(p, x) )

    #---- Terminals with whitespace

    def p_sel_ident( self, p ):
        """sel_ident    : SEL_IDENT wc
                        | SEL_IDENT"""
        x = [ (IDENT, 1), p[2] ] if len(p) == 3 else [ (IDENT, 1), None ]
        p[0] = Ident( p.parser, *self._buildterms(p, x) )

    def p_sel_string( self, p ):
        """sel_string   : SEL_STRING wc
                        | SEL_STRING"""
        x = [ (STRING, 1), p[2] ] if len(p) == 3 else [ (STRING, 1), None ]
        p[0] = String( p.parser, *self._buildterms(p, x) )

    def p_sel_hash( self, p ):
        """sel_hash     : SEL_HASH wc
                        | SEL_HASH"""
        (cls, value) = p[1]
        wc = p[2] if len(p) == 3 else None
        p[0] = Hash( p.parser, cls(p.parser, value), wc )

    def p_ident( self, p ):
        """ident        : IDENT wc
                        | IDENT"""
        x = [ (IDENT, 1), p[2] ] if len(p) == 3 else [ (IDENT, 1), None ]
        p[0] = Ident( p.parser, *self._buildterms(p, x) )

    def p_string( self, p ):
        """string       : STRING wc
                        | STRING"""
        x = [ (STRING, 1), p[2] ] if len(p) == 3 else [ (STRING, 1), None ]
        p[0] = String( p.parser, *self._buildterms(p, x) )

    def p_uri( self, p ):
        """uri          : URI wc
                        | URI"""
        x = [ (URI, 1), p[2] ] if len(p) == 3 else [ (URI, 1), None ]
        p[0] = Uri( p.parser, *self._buildterms(p, x) )

    def p_unicoderange( self, p ):
        """unicoderange : UNICODERANGE wc
                        | UNICODERANGE"""
        x = [ (UNICODERANGE, 1), p[2] 
            ] if len(p) == 3 else [ (UNICODERANGE, 1), None ]
        p[0] = UnicodeRange( p.parser, *self._buildterms(p, x) )

    def p_number( self, p ):
        """number       : NUMBER wc
                        | NUMBER"""
        (cls, value) = p[1]
        term = cls( p.parser, value )
        wc = p[2] if len(p) == 3 else None
        p[0] = Number( p.parser, term, wc )

    def p_dimension( self, p ):
        """dimension    : DIMENSION wc
                        | DIMENSION"""
        (cls, value) = p[1]
        term = cls( p.parser, value )
        wc = p[2] if len(p) == 3 else None
        p[0] = Dimension( p.parser, term, wc )

    def p_hash( self, p ):
        """hash         : HASH wc
                        | HASH"""
        (cls, value) = p[1]
        term = cls( p.parser, value )
        wc = p[2] if len(p) == 3 else None
        p[0] = Hash( p.parser, term, wc )

    def p_openbrace( self, p ):
        """openbrace    : OPENBRACE wc
                        | OPENBRACE"""
        t = OPENBRACE( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = Openbrace( p.parser, t, wc )

    def p_closebrace( self, p ):
        """closebrace   : CLOSEBRACE wc
                        | CLOSEBRACE"""
        t = CLOSEBRACE( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = Closebrace( p.parser, t, wc )

    def p_opensqr( self, p ):
        """opensqr      : OPENSQR wc
                        | OPENSQR"""
        t = OPENSQR( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = Opensqr( p.parser, t, wc )

    def p_closesqr( self, p ):
        """closesqr     : CLOSESQR wc
                        | CLOSESQR"""
        t = CLOSESQR( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = Closesqr( p.parser, t, wc )

    def p_openparan( self, p ):
        """openparan    : OPENPARAN wc
                        | OPENPARAN"""
        t = OPENPARAN( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = Openparan( p.parser, t, wc )

    def p_closeparan( self, p ):
        """closeparan   : CLOSEPARAN wc
                        | CLOSEPARAN"""
        t = CLOSEPARAN( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = Closeparan( p.parser, t, wc )

    def p_wc_1( self, p ):
        """wc           : S
                        | wc S"""
        args = [ p[1], S(p.parser, p[2]), None 
               ] if len(p) == 3 else  [ None, S(p.parser, p[1]), None ]
        p[0] = WC( p.parser, *args )

    def p_wc_2( self, p ):
        """wc           : COMMENT
                        | wc COMMENT"""
        args = [ p[1], None, COMMENT(p.parser, p[2])
               ] if len(p) == 3 else  [ None, None, COMMENT(p.parser, p[1]) ]
        p[0] = WC( p.parser, *args )

    #---- For confirmance with forward compatible CSS

    def p_error( self, p ):
        if p:
            column = self.tsslex._find_tok_column( p )
            self._parse_error( 'before: %s ' % (p.value,),
                               self._coord(p.lineno, column) )
        else:
            self._parse_error( 'At end of input', '' )

class Coord( object ):
    """ Coordinates of a syntactic element. Consists of:
        - File name
        - Line number
        - (optional) column number, for the Lexer
    """
    def __init__( self, file, line, column=None ):
        self.file   = file
        self.line   = line
        self.column = column

    def __str__( self ):
        str = "%s:%s" % (self.file, self.line)
        if self.column :
            str += ":%s" % self.column
        return str


if __name__ == "__main__":
    import pprint, time

    if len(sys.argv) > 1 :
        text = codecs.open( sys.argv[1], encoding='utf-8-sig' ).read()
    else :
        text = "hello"
    parser = TSSParser( yacc_debug=True )
    t1 = time.time()
    # set debuglevel to 2 for debugging
    t = parser.parse( text, 'x.c', debuglevel=2 )
    t.show( showcoord=True )
    print time.time() - t1
