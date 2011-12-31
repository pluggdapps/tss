# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Parser grammer for TSS Extension language"""

# Gotcha : None
#   1. To provide browser compliance, `operator` non-terminal can also have,
#           colon, equal, dot, gt, ask
#      like,
#           filter : progid:DXImageTransform.Microsoft.gradient(
#                       startColorstr='#c2080b',endColorstr='#8c0408',
#                       GradientType=0 )
# Notes  :
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

    def p_tss( self, p ):
        """tss          : stylesheet
                        | tss stylesheet"""
        args = [ p[1], p[2] ] if len(p)==3 else [ None, p[1] ]
        p[0] = Tss( p.parser, *args )
        # TODO : Makes sure that charset, import and namespace non-terminals
        # does not follow rulesets, media, page, font_face non-terminals

    def p_stylesheet( self, p ):
        """stylesheet   : cdata
                        | charset
                        | namespace
                        | font_face
                        | import
                        | media
                        | atrule
                        | rulesets
                        | wc"""
        p[0] = StyleSheet( p.parser, p[1] )

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

    #---- @import

    def p_import_1( self, p ):
        """import       : IMPORT_SYM string IDENT SEMICOLON
                        | IMPORT_SYM uri IDENT SEMICOLON"""
        mediums = Mediums( p.parser, None, None, None, IDENT(p.parser, p[3]) )
        x = [ (IMPORT_SYM, 1), p[2], mediums, (SEMICOLON, 4) ]
        p[0] = Import( p.parser, *self._buildterms(p, x) )

    def p_import_2( self, p ):
        """import       : IMPORT_SYM string IDENT S SEMICOLON
                        | IMPORT_SYM uri IDENT S SEMICOLON"""
        mediums = Mediums( p.parser, None, None, None, IDENT(p.parser, p[3]) )
        x = [ (IMPORT_SYM, 1), p[2], mediums, (SEMICOLON, 4) ]
        p[0] = Import( p.parser, *self._buildterms(p, x) )
        
    def p_import_3( self, p ):
        """import       : IMPORT_SYM string IDENT mediums SEMICOLON
                        | IMPORT_SYM uri IDENT mediums SEMICOLON"""
        mediums = Mediums( p.parser, None, None, None, IDENT(p.parser, p[3]) )
        p[4].pushident( mediums )
        x = [ (IMPORT_SYM, 1), p[2], p[4], (SEMICOLON, 5) ]
        p[0] = Import( p.parser, *self._buildterms(p, x) )

    def p_import_4( self, p ):
        """import       : IMPORT_SYM string SEMICOLON
                        | IMPORT_SYM uri SEMICOLON"""
        x = [ (IMPORT_SYM, 1), p[2], None, (SEMICOLON, 3) ]
        p[0] = Import( p.parser, *self._buildterms(p, x) )


    #---- @namespace

    def p_namespace_1( self, p ):
        """namespace    : NAMESPACE_SYM ident string SEMICOLON
                        | NAMESPACE_SYM ident uri SEMICOLON"""
        x = [ (NAMESPACE_SYM, 1), p[2], p[3], (SEMICOLON, 4) ]
        p[0] = Namespace( p.parser, *self._buildterms(p, x) )

    def p_namespace_2( self, p ):
        """namespace    : NAMESPACE_SYM string SEMICOLON
                        | NAMESPACE_SYM uri SEMICOLON"""
        x = [ (NAMESPACE_SYM, 1), None, p[2], (SEMICOLON, 3) ]
        p[0] = Namespace( p.parser, *self._buildterms(p, x) )

    #---- @media

    def p_media_1( self, p ):
        """media        : MEDIA_SYM exprs openbrace rulesets closebrace"""
        x = [ (MEDIA_SYM, 1), p[2], p[3], p[4], p[5] ]
        p[0] = Media( p.parser, *self._buildterms(p, x) )

    def p_media_2( self, p ):
        """media        : MEDIA_SYM exprs openbrace closebrace"""
        x = [ (MEDIA_SYM, 1), p[2], p[3], None, p[4] ]
        p[0] = Media( p.parser, *self._buildterms(p, x) )

    def p_mediums_1( self, p ):
        """mediums      : mediums S COMMA IDENT"""
        cls, val = p[3]
        x = [ p[1], (S, 2), cls(p.parser, val), (IDENT, 4) ]
        p[0] = Mediums( p.parser, *self._buildterms(p, x) )

    def p_mediums_2( self, p ):
        """mediums      : mediums COMMA IDENT"""
        cls, val = p[2]
        x = [ p[1], None, cls(p.parser, val), (IDENT, 3) ]
        p[0] = Mediums( p.parser, *self._buildterms(p, x) )

    def p_mediums_3( self, p ):
        """mediums      : COMMA IDENT"""
        cls, val = p[1]
        x = [ None, None, cls(p.parser, val), (IDENT, 2) ]
        p[0] = Mediums( p.parser, *self._buildterms(p, x) )

    def p_mediums_4( self, p ):
        """mediums      : S COMMA IDENT"""
        cls, val = p[2]
        x = [ None, (S, 2), cls(p.parser, val), (IDENT, 3) ]
        p[0] = Mediums( p.parser, *self._buildterms(p, x) )

    #---- @page

    def p_page_1( self, p ):
        """page         : PAGE_SYM ident block"""
        x = [ (PAGE_SYM, 1), p[2], None, None, p[3] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_page_2( self, p ):
        """page         : PAGE_SYM COLON ident block"""
        cls, val = p[2]
        x = [ (PAGE_SYM, 1), None, cls(p.parser, val), p[3], p[4] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_page_3( self, p ):
        """page         : PAGE_SYM ident COLON ident block"""
        cls, val = p[3]
        x = [ (PAGE_SYM, 1), p[2], cls(p.parser, val), p[4], p[4] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

    def p_page_4( self, p ):
        """page         : PAGE_SYM block"""
        x = [ (PAGE_SYM, 1), None, None, None, p[2] ]
        p[0] = Page( p.parser, *self._buildterms(p, x) )

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
        p[0] = AtRule( p.parser, term, p[2], None, None, (p[3], p[4], p[5]) )

    def p_atrule_6( self, p ):
        """atrule       : ATKEYWORD openbrace rulesets closebrace"""
        term = ATKEYWORD(p.parser, p[1])
        p[0] = AtRule( p.parser, term, None, None, None, (p[2], p[3], p[4]) )

    #---- ruleset

    # TODO : only `&` is allowd in DLIMIT terminal, this constraint should
    # be checked inside `ElementName` class
    def p_rulesets( self, p ):
        """rulesets     : ruleset
                        | page
                        | rulesets ruleset
                        | rulesets page"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None, p[1] ]
        p[0] = Rulesets( p.parser, *args )

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
        """selector     : simpselector"""
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
        """simpselector : sel_ident"""
        p[0] = SimpleSelector( p.parser, None, None, p[1], None, None, None )

    def p_simpselector_2( self, p ):
        """simpselector : sel_hash"""
        p[0] = SimpleSelector( p.parser, None, None, None, p[1], None, None )

    def p_simpselector_3( self, p ):
        """simpselector : SEL_STAR"""
        cls, value = p[1]
        term = cls(p.parser, value)
        p[0] = SimpleSelector( p.parser, term, None, None, None, None, None )

    def p_simpselector_4( self, p ):
        """simpselector : DOT sel_ident"""
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
        """attrib       : opensqr sel_ident closesqr"""
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
        """pseudo       : SEL_COLON SEL_COLON sel_ident
                        | SEL_COLON SEL_COLON func_call"""
        cls1, val1 = p[1]
        cls2, val2 = p[2]
        p[0] = Pseudo( p.parser, cls1(p.parser,val1), cls2(p.parser,val2), p[3] )

    #---- Declaration block

    def p_block( self, p ):
        """block        : openbrace declarations closebrace
                        | openbrace closebrace"""
        args = [ p[1], p[2], p[3] ] if len(p) == 4 else [ p[1], None, p[2] ]
        p[0] = Block( p.parser, *args )

    def p_declarations_1( self, p ):
        """declarations : declaration
                        | rulesets"""
        p[0] = Declarations( p.parser, None, None, None, p[1] )

    def p_declarations_2( self, p ):
        """declarations : declarations SEMICOLON"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, None, None )

    def p_declarations_3( self, p ):
        """declarations : declarations SEMICOLON declaration"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, None, p[3] )

    def p_declarations_4( self, p ):
        """declarations : declarations SEMICOLON wc"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, p[3], None )

    def p_declarations_5( self, p ):
        """declarations : declarations SEMICOLON wc declaration"""
        term = SEMICOLON( p.parser, p[2] )
        p[0] = Declarations( p.parser, p[1], term, p[3], p[4] )

    def p_declarations_6( self, p ):
        """declarations : declarations rulesets"""
        p[0] = Declarations( p.parser, p[1], None, None, p[3] )

    def p_declaration_1( self, p ):
        """declaration  : ident COLON exprs prio"""
        cls, value = p[2]
        x = [ None, p[1], cls(p.parser, value), p[3], p[4] ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_declaration_2( self, p ):
        """declaration  : ident COLON exprs"""
        cls, value = p[2]
        x = [ None, p[1], cls(p.parser, value), p[3], None ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_declaration_3( self, p ):
        """declaration  : PREFIXSTAR ident COLON exprs prio"""
        cls1, val1 = p[1]
        cls2, val2 = p[3]
        x = [ cls1(p.parser, val1), p[2], cls2(p.parser, val2), p[4], p[5] ]
        p[0] = Declaration( p.parser, *self._buildterms(p, x) )

    def p_declaration_4( self, p ):
        """declaration  : PREFIXSTAR ident COLON exprs"""
        cls1, val1 = p[1]
        cls2, val2 = p[3]
        x = [ cls1(p.parser, val1), p[2], cls2(p.parser, val2), p[4], None ]
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
        """expr         : openparan expr closeparan"""
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
                        | expr FWDSLASH expr
                        | expr AND expr
                        | expr OR expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, p[1], term, p[3] )

    def p_expr_5( self, p ):
        """expr         : expr EQUAL expr
                        | expr GT expr
                        | expr LT expr"""
        cls, value = p[2]
        term = cls(p.parser, value)
        p[0] = Expr( p.parser, None, None, p[1], term, p[3] )

    def p_expr_6( self, p ):
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

    def p_term( self, p ):
        """term         : number
                        | dimension
                        | func_call
                        | ident
                        | string
                        | uri
                        | unicoderange
                        | hash"""
        p[0] = Term( p.parser, p[1] )

    def p_func_call_1( self, p ):
        """func_call    : FUNCTION exprs closeparan"""
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
