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

import logging, re, sys, copy
from   types        import StringType
from   os.path      import splitext, dirname
from   hashlib      import sha1

import ply.yacc
from   tss.lexer    import TSSLexer
from   tss.ast      import *

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
                  outputdir='',
                  lex_debug=None,
                  yacc_debug=None,
                  debug=None
                ) :
        """
        Create a new TSSParser.

        ``tssconfig``
            All configurations related to tayra templates, are represented in
            this object.

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
        optimize = tssconfig.get( 'parse_optimize', False )
        lextab = tssconfig.get( 'lextab', LEXTAB ) or LEXTAB
        yacctab = tssconfig.get( 'yacctab', YACCTAB ) or YACCTAB
        # Build Lexer
        self.tsslex = TSSLexer( error_func=self._lex_error_func )
        kwargs = { 'optimize' : optimize } if optimize else {}
        kwargs.update( debug=lex_debug )
        kwargs.update( lextab=lextab ) if lextab else None
        self.tsslex.build( **kwargs )
        # Build Yaccer
        kwargs = { 'optimize' : optimize } if optimize else {}
        kwargs.update( debug=yacc_debug )
        kwargs.update( outputdir=outputdir ) if outputdir else None
        kwargs.update( tabmodule=yacctab )
        self.parser = ply.yacc.yacc( module=self, **kwargs )
        self.parser.tssparser = self        # For AST nodes to access `this`
        # Parser initialization
        self._tssconfig = tssconfig
        self._initialize()

    def _initialize( self ) :
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
        self.hashtext = sha1( text ).hexdigest()

        # parse and get the Translation Unit
        debuglevel = self.debug or debuglevel
        self.tu = self.parser.parse( text, lexer=self.tsslex, debug=debuglevel )
        return self.tu

    # ------------------------- Private functions -----------------------------

    def _lex_error_func( self, lex, msg, line, column ):
        self._parse_error( msg, self._coord( line, column ))
    
    def _coord( self, lineno, column=None ):
        return Coord( file=self.tsslex.filename, line=lineno, column=column )
    
    def _parse_error(self, msg, coord):
        raise ParseError("%s: %s" % (coord, msg))

    def _printparse( self, p ) :
        print p[0], "  : ",
        for i in range(1,len(p)) :
            print p[i],
        print

    # ---------- Precedence and associativity of operators --------------------

    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('right', 'UNARY'),
    )

    def _buildterms( self, p, terms ) :
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

    def p_tss( self, p ) :
        """tss          : stylesheets"""
        p[0] = Tss( p.parser, p[1] )

    def p_stylesheets_1( self, p ) :
        """stylesheets  : stylesheet"""
        p[0] = StyleSheets( p.parser, None, p[1] )

    def p_stylesheets_2( self, p ) :
        """stylesheets  : stylesheets stylesheet"""
        p[0] = StyleSheets( p.parser, p[1], p[2] )

    def p_stylesheet( self, p ) :
        """stylesheet   : cdatas
                        | charset
                        | import
                        | namespace
                        | statement"""
        p[0] = StyleSheet( p.parser, p[1] )

    def p_statement( self, p ) :
        """statement    : page
                        | font_face
                        | media
                        | atrule
                        | rulesets
                        | functiondef
                        | extn_statement
                        | wc"""
        p[0] = Statement( p.parser, p[1] )

    #---- CDATA

    def p_cdatas( self, p ) :
        """cdatas       : cdata
                        | cdatas cdata"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None,  p[1] ]
        p[0] = Cdatas( p.parser, *args )

    def p_cdata( self, p ) :
        """cdata        : cdo cdc
                        | cdo cdata_conts cdc"""
        args = [ p[1], p[2], p[3] ] if len(p) == 4 else [ p[1], None, p[2] ]
        p[0] = Cdata( p.parser, *args )

    def p_cdata_conts( self, p ) :
        """cdata_conts  : cdata_cont
                        | cdata_conts cdata_cont"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None, p[1] ]
        p[0] = CdataConts( p.parser, *args )

    def p_cdata_cont( self, p ) :
        """cdata_cont   : expr
                        | any
                        | operator
                        | block"""
        p[0] = CdataCont( p.parser, p[1] )

    #---- @charset 

    def p_charset( self, p ) :
        """charset      : charset_sym string SEMICOLON
                        | charset_sym extn_expr SEMICOLON"""
        p[0] = Charset( p.parser, p[1], p[2], SEMICOLON(p.parser, p[3]) )

    #---- @import

    def p_import( self, p ) :
        """import       : import_sym string mediums SEMICOLON
                        | import_sym string SEMICOLON
                        | import_sym uri mediums SEMICOLON
                        | import_sym uri SEMICOLON
                        | import_sym extn_expr mediums SEMICOLON
                        | import_sym extn_expr SEMICOLON"""
        args = [ p[1], p[2], p[3], SEMICOLON(p.parser, p[4])
               ] if len(p) == 5 else [ p[1],p[2],None,SEMICOLON(p.parser,p[3]) ]
        p[0] = Import( p.parser, *args )

    #---- @namespace

    def p_namespace_1( self, p ) :
        """namespace    : namespace_sym nmprefix string SEMICOLON
                        | namespace_sym nmprefix uri SEMICOLON
                        | namespace_sym nmprefix extn_expr SEMICOLON"""
        p[0] = Namespace(p.parser, p[1], p[2], p[3], SEMICOLON(p.parser, p[4]))

    def p_namespace_2( self, p ) :
        """namespace    : namespace_sym string SEMICOLON
                        | namespace_sym uri SEMICOLON
                        | namespace_sym extn_expr SEMICOLON"""
        p[0] = Namespace(p.parser, p[1], None, p[2], SEMICOLON(p.parser, p[4]))

    def p_nmprefix( self, p ) :
        """nmprefix     : ident
                        | extn_expr"""
        p[0] = NamePrefix( p.parser, p[1] )

    #---- @page

    def p_page_1( self, p ) :
        """page         : page_sym IDENT pseudo_page block"""
        p[0] = Page( p.parser, p[1], IDENT(p.parser, p[2]), p[3], p[4] )

    def p_page_2( self, p ) :
        """page         : page_sym ident block
                        | page_sym pseudo_page block"""
        p[0] = Page( p.parser, p[1], None, p[2], p[3] )

    def p_pseudo_page( self, p ) :
        """pseudo_page  : COLON ident"""
        p[0] = PseudoPage( p.parser, COLON(p.parser, p[1]), p[2] )

    #---- @font_face

    def p_font_face( self, p ) :
        """font_face    : font_face_sym block"""
        p[0] = FontFace( p.parser, p[1], p[2] )

    #---- @media

    def p_media_1( self, p ) :
        """media        : media_sym mediums openbrace rulesets closebrace"""
        decl = Declarations( p.parser, None, None, p[4] )
        bloc = Block( p[3], decl, p[5] )
        p[0] = Media( p.parser, p[1], p[2], bloc )

    def p_media_2( self, p ) :
        """media        : media_sym mediums openbrace closebrace"""
        bloc = Block( p[3], None, p[4] )
        p[0] = Media( p.parser, p[1], p[2], block )

    def p_mediums( self, p ) :
        """mediums      : medium
                        | mediums medium
                        | mediums comma medium"""
        if len(p) == 4 :
            args = [ p[1], p[2], p[3] ]
        else :
            args = [ p[1], None, p[2] ] if len(p) == 3 else [None, None, p[1]]
        p[0] = Mediums( p.parser, *args )

    def p_medium( self, p ) :
        """medium       : expr
                        | any"""
        p[0] = Medium( p.parser, p[1] )

    #---- atrule

    # Gotcha : Handle generic at-rules
    def p_atrule_1( self, p ) :
        """atrule       : atkeyword expr block"""
        p[0] = AtRule( p.parser, p[1], p[2], None, p[3] )

    def p_atrule_2( self, p ) :
        """atrule       : atkeyword expr SEMICOLON"""
        semi = SEMICOLON(p.parser, p[3])
        p[0] = AtRule( p.parser, p[1], p[2], semi, None )

    def p_atrule_3( self, p ) :
        """atrule       : atkeyword block"""
        p[0] = AtRule( p.parser, p[1], None, None, p[2] )

    def p_atrule_4( self, p ) :
        """atrule       : atkeyword SEMICOLON"""
        semi = SEMICOLON(p.parser, p[2])
        p[0] = AtRule( p.parser, p[1], None, semi, None )

    def p_atrule_5( self, p ) :
        """atrule       : atkeyword expr openbrace rulesets closebrace"""
        decl = Declarations( p.parser, None, None, p[4] )
        bloc = Block( p[3], decl, p[5] )
        p[0] = AtRule( p.parser, p[1], p[2], None, bloc )

    def p_atrule_6( self, p ) :
        """atrule       : atkeyword openbrace rulesets closebrace"""
        decl = Declarations( p.parser, None, None, p[3] )
        bloc = Block( p[2], decl, p[4] )
        p[0] = AtRule( p.parser, p[1], None, None, bloc )

    #---- ruleset

    def p_rulesets( self, p ) :
        """rulesets     : ruleset 
                        | rulesets ruleset"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None, p[1] ]
        p[0] = RuleSets( p.parser, *args )

    def p_ruleset_1( self, p ) :
        """ruleset      : block
                        | ifelfiblock
                        | forblock
                        | whileblock"""
        p[0] = RuleSet( p.parser, p[1] )

    def p_ruleset_2( self, p ) :
        """ruleset      : selectors block"""
        p[0] = RuleSet( p.parser, p[1], p[2] )

    def p_ruleset_3( self, p ) :
        """ruleset      : PERCENT ident block
                        | PERCENT ident expr block"""
        perc = PERCENT( p.parser, p[1] )
        args = [ perc, p[2], p[3], p[4] 
               ] if len(p) == 5 else [ perc, p[2], None, p[3] ]
        p[0] = RuleSet( p.parser, *args, namespace_ext=True )

    def p_selectors_1( self, p ) :
        """selectors    : selector"""
        p[0] = Selectors( p.parser, None, None, p[1] )

    def p_selectors_2( self, p ) :
        """selectors    : selectors comma"""
        p[0] = Selectors( p.parser, p[1], p[2], None )

    def p_selectors_3( self, p ) :
        """selectors    : selectors comma selector"""
        p[0] = Selectors( p.parser, p[1], p[2], p[3] )

    def p_selector_1( self, p ) :
        """selector     : simple_selector"""
        p[0] = Selector( p.parser, None, None, p[1] )

    def p_selector_2( self, p ) :
        """selector     : selector simple_selector"""
        p[0] = Selector( p.parser, p[1], None, p[2] )

    def p_selector_3( self, p ) :
        """selector     : selector combinator simple_selector"""
        p[0] = Selector( p.parser, p[1], p[2], p[3] )

    def p_simple_selector_1( self, p ) :
        """simple_selector  : element_name"""
        p[0] = SimpleSelector( p.parser, None, p[1], None, None )

    def p_simple_selector_2( self, p ) :
        """simple_selector  : extender"""
        p[0] = SimpleSelector( p.parser, None, None, p[1], None )

    def p_simple_selector_3( self, p ) :
        """simple_selector  : extn_expr"""
        p[0] = SimpleSelector( p.parser, None, None, None, p[1] )

    def p_simple_selector_4( self, p ) :
        """simple_selector  : simple_selector extender"""
        p[0] = SimpleSelector( p.parser, p[1], None, p[2], None )

    def p_element_name( self, p ) :
        """element_name : ident
                        | star
                        | DLIMIT"""
        # only `&` is allowd in DLIMIT terminal, this constraint should be
        # checked inside `ElementName` class
        p[0] = ElementName( p.parser, p[1] )

    def p_combinator( self, p ) :
        """combinator   : plus
                        | gt
                        | tilda"""
        p[0] = Combinator( p.parser, p[1] )

    def p_extender( self, p ) :
        """extender     : hash
                        | class
                        | attrib
                        | pseudo"""
        p[0] = Extender( p.parser, p[1] )

    def p_class( self, p ) :
        """class        : DOT IDENT
                        | DOT IDENT wc"""
        x = [ (DOT, 1), (IDENT, 2) ]
        x.append( p[3] if len(p) == 4 else None )
        p[0] = Class( p.parser, *self._buildterms( p, x ) )

    def p_attrib_1( self, p ) :
        """attrib       : opensqr ident attr_oper attr_val closesqr"""
        p[0] = Attrib( p.parser, p[1], p[2], p[3], p[4], p[5] )

    def p_attrib_2( self, p ) :
        """attrib       : opensqr ident closesqr"""
        p[0] = Attrib( p.parser, p[1], p[2], None, None, p[3] )

    def p_attroper( self, p ) :
        """attr_oper    : equal
                        | includes
                        | dashmatch
                        | prefixmatch
                        | suffixmatch
                        | substringmatch"""
        p[0] = AttrOper( p.parser, p[1] )

    def p_attrval( self, p ) :
        """attr_val     : ident
                        | string"""
        p[0] = AttrVal( p.parser, p[1] )

    def p_pseudo( self, p ) :
        """pseudo       : COLON pseudo_name
                        | COLON COLON pseudo_name"""
        args = [ COLON(p.parser, p[1]), COLON(p.parser, p[2]), p[3] 
               ] if len(p) == 4 else [ COLON(p.parser, p[1]), None, p[2] ]
        p[0] = Pseudo( p.parser, *args )

    def p_pseudoname_1( self, p ) :
        """pseudo_name  : ident"""
        p[0] = PseudoName( p.parser, p[1], None, None, None )

    def p_pseudoname_2( self, p ) :
        """pseudo_name  : function simple_selector closeparan
                        | function string closeparan
                        | function number closeparan"""
        p[0] = PseudoName( p.parser, None, p[1], p[2], p[3] )

    #---- block

    #def p_blocks( self, p ) :
    #    """blocks       : block
    #                    | blocks block"""
    #    args = [ p[1], p[2] ] if len(p) == 3 else [ None, p[1] ]
    #    p[0] = Blocks( p.parser, *args )

    def p_block( self, p ) :
        """block        : openbrace declarations closebrace
                        | openbrace closebrace"""
        args = [ p[1], p[2], p[3] ] if len(p) == 4 else [ p[1], None, p[2] ]
        p[0] = Block( p.parser, *args )

    def p_declarations( self, p ) :
        """declarations : declaration
                        | rulesets
                        | extn_statement
                        | declarations semicolon
                        | declarations semicolon declaration
                        | declarations semicolon rulesets
                        | declarations semicolon extn_statement"""
        if len(p) == 4 :
            args = [ p[1], p[2], p[3] ]
        elif len(p) == 3 :
            args = [ p[1], p[2], None ]
        else :
            args = [ None, None, p[1] ]
        p[0] = Declarations( p.parser, *args )

    def p_declaration_1( self, p ) :
        """declaration  : ident colon expr prio
                        | ident colon expr"""
        args = [ None, p[1], None, p[2], p[3], p[4] 
               ] if len(p) == 5 else [ None, p[1], None, p[2], p[3], None ]
        p[0] = Declaration( p.parser, *args )

    def p_declaration_2( self, p ) :
        """declaration  : extn_expr colon expr prio
                        | extn_expr colon expr"""
        args = [ None, None, p[1], p[2], p[3], p[4] 
               ] if len(p) == 5 else [ None, None, p[1], p[2], p[3], None ]
        p[0] = Declaration( p.parser, *args )

    def p_declaration_3( self, p ) :
        """declaration  : star ident colon expr prio
                        | star ident colon expr"""
        args = [ p[1], p[2], None, p[3], p[4], p[5] 
               ] if len(p) == 6 else [ p[1], p[2], None, p[3], p[4], None ]
        p[0] = Declaration( p.parser, *args )

    def p_prio( self, p ) :
        """prio         : important_sym"""
        p[0] = Priority( p.parser, p[1] )

    #---- expr

    def p_expr( self, p ) :
        """expr         : binaryexpr
                        | expr binaryexpr"""
        args = [ p[1], p[2] ] if len(p) == 3 else [ None,  p[1] ]
        p[0] = Expr( p.parser, *args )

    def p_binaryexpr( self, p ) :
        """binaryexpr   : term
                        | unaryexpr
                        | extn_expr
                        | binaryexpr operator binaryexpr"""
        args = [ None, None, None, p[1] 
               ] if len(p) == 2 else [ p[1], p[2], p[3], None ]
        p[0] = BinaryExpr( p.parser, *args )

    def p_unaryexpr_1( self, p ) :
        """unaryexpr    : openparan expr closeparan"""
        p[0] = UnaryExpr( p.parser, None, None, (p[1], p[2], p[3]) )

    def p_unaryexpr_2( self, p ) :
        """unaryexpr    : plus term_val %prec UNARY
                        | minus term_val %prec UNARY"""
        p[0] = UnaryExpr( p.parser, p[1], p[2], None )

    def p_term( self, p ) :
        """term         : term_val
                        | string
                        | ident
                        | uri
                        | unicoderange
                        | hash"""
        # Note : here hash should be hex-color #[0-9a-z]{3} or #[0-9a-z]{6}
        # Perform the contstraint check inside the `Term` class
        p[0] = Term( p.parser, p[1])

    def p_term_val( self, p ) :
        """term_val     : number
                        | percentage
                        | dimension
                        | func_call"""
        p[0] = TermVal( p.parser, p[1] )
                         
    def p_func( self, p ) :
        """func_call    : function expr closeparan
                        | function closeparan"""
        args = [ p[1], p[2], p[3] ] if len(p) == 4 else [ p[1], None, p[2] ]
        p[0] = FuncCall( p.parser, *args )

    # Note : `operator` should never be a `SEMICOLON`,
    #        as per CSS3 grammar only, fwdslash and comma are real operators
    def p_operator( self, p ) :
        """operator     : fwdslash
                        | comma
                        | colon
                        | dot
                        | equal
                        | gt
                        | lt
                        | plus
                        | minus
                        | star
                        | dlimit"""
        p[0] = Operator( p.parser, p[1] )

    #def p_unary_oper( self, p ) :
    #    """unary_oper   : plus
    #                    | minus"""
    #    p[0] = Unary( p.parser, p[1] )

    #---- Terminals with whitespace

    def p_charset_sym( self, p ) :
        """charset_sym  : CHARSET_SYM wc
                        | CHARSET_SYM"""
        t = CHARSET_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_import_sym( self, p ) :
        """import_sym   : IMPORT_SYM wc
                        | IMPORT_SYM"""
        t = IMPORT_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_namespace_sym( self, p ) :
        """namespace_sym : NAMESPACE_SYM wc
                         | NAMESPACE_SYM"""
        t = NAMESPACE_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_media_sym( self, p ) :
        """media_sym    : MEDIA_SYM wc
                        | MEDIA_SYM"""
        t = MEDIA_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_page_sym( self, p ) :
        """page_sym     : PAGE_SYM wc
                        | PAGE_SYM"""
        t = PAGE_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_font_face_sym( self, p ) :
        """font_face_sym : FONT_FACE_SYM wc
                         | FONT_FACE_SYM"""
        t = FONT_FACE_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_important_sym( self, p ) :
        """important_sym : IMPORTANT_SYM wc
                         | IMPORTANT_SYM"""
        t = IMPORTANT_SYM( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_atkeyword( self, p ) :
        """atkeyword    : ATKEYWORD wc
                        | ATKEYWORD"""
        t = ATKEYWORD( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_string( self, p ) :
        """string       : STRING wc
                        | STRING"""
        t = STRING( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_uri( self, p ) :
        """uri          : URI wc
                        | URI"""
        t = URI( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_function( self, p ) :
        """function     : FUNCTION wc
                        | FUNCTION"""
        t = FUNCTION( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_unicoderange( self, p ) :
        """unicoderange : UNICODERANGE wc
                        | UNICODERANGE"""
        t = UNICODERANGE( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_ident( self, p ) :
        """ident        : IDENT wc
                        | IDENT"""
        t = IDENT( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_number( self, p ) :
        """number       : NUMBER wc
                        | NUMBER"""
        t = NUMBER( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_percentage( self, p ) :
        """percentage   : PERCENTAGE wc
                        | PERCENTAGE"""
        t = PERCENTAGE( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_dimension( self, p ) :
        """dimension    : DIMENSION wc
                        | DIMENSION"""
        t = DIMENSION( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_fwdslash( self, p ) :
        """fwdslash     : FWDSLASH wc
                        | FWDSLASH"""
        t = FWDSLASH( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_comma( self, p ) :
        """comma        : COMMA wc
                        | COMMA"""
        t = COMMA( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_hash( self, p ) :
        """hash         : HASH wc
                        | HASH"""
        t = HASH( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_equal( self, p ) :
        """equal        : EQUAL wc
                        | EQUAL"""
        t = EQUAL( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_includes( self, p ) :
        """includes     : INCLUDES wc
                        | INCLUDES"""
        t = INCLUDES( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_dashmatch( self, p ) :
        """dashmatch    : DASHMATCH wc
                        | DASHMATCH"""
        t = DASHMATCH( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_prefixmatch( self, p ) :
        """prefixmatch  : PREFIXMATCH wc
                        | PREFIXMATCH"""
        t = PREFIXMATCH( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_suffixmatch( self, p ) :
        """suffixmatch  : SUFFIXMATCH wc
                        | SUFFIXMATCH"""
        t = SUFFIXMATCH( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_substringmatch( self, p ) :
        """substringmatch   : SUBSTRINGMATCH wc
                            | SUBSTRINGMATCH"""
        t = SUBSTRINGMATCH( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_plus( self, p ) :
        """plus         : PLUS wc
                        | PLUS"""
        t = PLUS( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_minus( self, p ) :
        """minus        : MINUS wc
                        | MINUS"""
        t = MINUS( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_gt( self, p ) :
        """gt           : GT wc
                        | GT"""
        t = GT( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_lt( self, p ) :
        """lt           : LT wc
                        | LT"""
        t = LT( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_tilda( self, p ) :
        """tilda        : TILDA wc
                        | TILDA"""
        t = TILDA( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_colon( self, p ) :
        """colon        : COLON wc
                        | COLON"""
        t = COLON( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_semicolon( self, p ) :
        """semicolon    : SEMICOLON wc
                        | SEMICOLON"""
        t = SEMICOLON( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_star( self, p ) :
        """star         : STAR wc
                        | STAR"""
        t = STAR( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_dot( self, p ) :
        """dot          : DOT wc
                        | DOT"""
        t = DOT( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_dlimit( self, p ) :
        """dlimit       : DLIMIT wc
                        | DLIMIT"""
        t = DLIMIT( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_openbrace( self, p ) :
        """openbrace    : OPENBRACE wc
                        | OPENBRACE"""
        t = OPENBRACE( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_closebrace( self, p ) :
        """closebrace   : CLOSEBRACE wc
                        | CLOSEBRACE"""
        t = CLOSEBRACE( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_opensqr( self, p ) :
        """opensqr      : OPENSQR wc
                        | OPENSQR"""
        t = OPENSQR( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_closesqr( self, p ) :
        """closesqr     : CLOSESQR wc
                        | CLOSESQR"""
        t = OPENSQR( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_openparan( self, p ) :
        """openparan    : OPENPARAN wc
                        | OPENPARAN"""
        t = OPENPARAN( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_closeparan( self, p ) :
        """closeparan   : CLOSEPARAN wc
                        | CLOSEPARAN"""
        t = CLOSEPARAN( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_wc_1( self, p ) :
        """wc           : S
                        | wc S"""
        args = [ p[1], S(p.parser, p[2]), None 
               ] if len(p) == 3 else  [ None, S(p.parser, p[1]), None ]
        p[0] = WC( p.parser, *args )

    def p_wc_2( self, p ) :
        """wc           : COMMENT
                        | wc COMMENT"""
        args = [ p[1], None, COMMENT(p.parser, p[2])
               ] if len(p) == 3 else  [ None, None, COMMENT(p.parser, p[1]) ]
        p[0] = WC( p.parser, *args )

    def p_cdo( self, p ) :
        """cdo          : CDO wc
                        | CDO"""
        t = CDO( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_cdc( self, p ) :
        """cdc          : CDC wc
                        | CDC"""
        t = CDC( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    #---- Extension language specific grammars

    def p_functionstart( self, p ) :
        """functionstart    : FUNCTIONSTART wc
                            | FUNCTIONSTART"""
        t = FUNCTIONSTART( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_functionbody( self, p ) :
        """functionbody : FUNCTIONBODY wc
                        | FUNCTIONBODY"""
        t = FUNCTIONBODY( p.parser, p[1] )
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, t, wc )

    def p_extn_expr( self, p ) :
        """extn_expr    : EXTN_EXPR wc
                        | EXTN_EXPR"""
        wc = p[2] if len(p) == 3 else None
        p[0] = ExtnExpr( p.parser, EXTN_EXPR(p.parser, p[1]), wc )

    def p_extn_statement( self, p ) :
        """extn_statement   : EXTN_STATEMENT wc
                            | EXTN_STATEMENT"""
        wc = p[2] if len(p) == 3 else None
        p[0] = ExtnStatement( p.parser, EXTN_STATEMENT(p.parser, p[1]), wc )

    def p_ifcontrol( self, p ) :
        """ifcontrol    : IFCONTROL wc
                        | IFCONTROL"""
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, IFCONTROL(p.parser, p[1]), wc )

    def p_elifcontrol( self, p ) :
        """elifcontrol  : ELIFCONTROL wc
                        | ELIFCONTROL"""
        wc = p[2] if len(p) == 3 else None
        p[0] = TerminalS( p.parser, ELIFCONTROL(p.parser, p[1]), wc )

    def p_elsecontrol( self, p ) :
        """elsecontrol  : ELSECONTROL wc
                        | ELSECONTROL"""
        p[0] = TerminalS( p.parser, ELSECONTROL(p.parser, p[1]), wc )

    def p_forcontrol( self, p ) :
        """forcontrol   : FORCONTROL wc
                        | FORCONTROL"""
        p[0] = TerminalS( p.parser, FORCONTROL(p.parser, p[1]), wc )

    def p_whilecontrol( self, p ) :
        """whilecontrol : WHILECONTROL wc
                        | WHILECONTROL"""
        p[0] = TerminalS( p.parser, WHILECONTROL(p.parser, p[1]), wc )

    def p_functiondef( self, p ) :
        """functiondef  : functionstart functionbody"""
        p[0] = FunctionDef( p.parser, p[1], p[2] )

    def p_ifelfiblock_1( self, p ) :
        """ifelfiblock  : ifblock"""
        p[0] = IfelfiBlock( p.parser, p[1], None, None )

    def p_ifelfiblock_2( self, p ) :
        """ifelfiblock  : ifelfiblock elifblock
                        | ifelfiblock elseblock"""
        p[0] = IfelfiBlock( p.parser, None, p[1], p[2] )

    def p_ifblock( self, p ) :
        """ifblock      : ifcontrol declarations closebrace"""
        p[0] = IfBlock( p.parser, p[1], p[2], p[3] )

    def p_elifblock( self, p ) :
        """elifblock    : elifcontrol declarations closebrace"""
        p[0] = ElifBlock( p.parser, p[1], p[2], p[3] )

    def p_elseblock( self, p ) :
        """elseblock    : elsecontrol declarations closebrace"""
        p[0] = ElseBlock( p.parser, p[1], p[2], p[3] )

    def p_forblock( self, p ) :
        """forblock     : forcontrol declarations closebrace"""
        p[0] = ForBlock( p.parser, p[1], p[2], p[3] )

    def p_whileblock( self, p ) :
        """whileblock   : whilecontrol declarations closebrace"""
        p[0] = WhileBlock( p.parser, p[1], p[2], p[3] )

    #---- For confirmance with forward compatible CSS

    def p_any( self, p) :
        """any          : opensqr expr closesqr"""
        p[0] = Any( p.parser, p[1], p[2], p[3] )

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
    
    text   = open(sys.argv[1]).read() if len(sys.argv) > 1 else "hello" 
    parser = TSSParser(
                lex_optimize=True, yacc_debug=True, yacc_optimize=False
             )
    t1     = time.time()
    # set debuglevel to 2 for debugging
    t = parser.parse( text, 'x.c', debuglevel=2 )
    t.show( showcoord=True )
    print time.time() - t1
