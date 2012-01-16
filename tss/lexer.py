#! /usr/bin/env python

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Lexing rules for TSS Extension language based on CSS3 token rules."""

# Gotcha :
#   1. `nmchar` and `nmstart` supports Case-insensitive identifiers (seems to
#   be not in sync with CSS spec. ??
# Notes  :
# Todo   :


import re, sys, logging, codecs
import ply.lex
from   ply.lex      import TOKEN

from   tss.ast      import EMS, EXS, LENGTHPX, LENGTHCM, LENGTHMM, LENGTHIN, \
                           LENGTHPT, LENGTHPC, ANGLEDEG, ANGLERAD, ANGLEGRAD, \
                           TIMEMS, TIMES, FREQHZ, FREQKHZ, PERCENTAGE, NUMBER, \
                           HASH, PLUS, MINUS, STAR, FWDSLASH, PERCENT, EQUAL, \
                           GT, LT, TILDA, COMMA, COLON, DOT, AMPERSAND, AND, \
                           OR, PREFIXSTAR, QMARK, INCLUDES, DASHMATCH, \
                           PREFIXMATCH, SUFFIXMATCH, SUBSTRINGMATCH, \
                           EXTN_EXPR, EXTN_STATEMENT, EXTN_VAR

log = logging.getLogger( __name__ )

class TSSLexer( object ) :
    """A lexer for the TSS Extension language.
        * build(), to build   
        * input(), set the input text
        * token(), to get new tokens.
    The public attribute filename can be set to an initial filaneme, but the
    lexer will update it upon #line directives."""

    ## -------------- Internal auxiliary methods ---------------------

    def _error( self, msg, token ):
        print "Error in file %r ..." % self.filename
        loct = self._make_tok_location( token )
        self.error_func and self.error_func( self, msg, loct[0], loct[1] )
        self.lexer.skip( 1 )
        log.error( "%s %s" % (msg, token) )
    
    def _find_tok_column( self, token ):
        i = token.lexpos
        while i > 0:
            if self.lexer.lexdata[i] == u'\n': break
            i -= 1
        return (token.lexpos - i) + 1
    
    def _make_tok_location( self, token ):
        return ( token.lineno, self._find_tok_column(token) )

    def _checkstmt( self, token ):
        val = token.value
        if val.endswith('\n') or val.endswith('\r\n') :
            n, data = self.lexer.lexpos, token.lexer.lexdata
            l = len(data)
            while (n<l) and (data[n] in ' \t') : n += 1
            token.lexer.push_state('statement') if (n<l) and (data[n]=='$') else None

    def _incrlineno( self, token ) :
        newlines = token.value.count(u'\n')
        if newlines > 0 :
            token.lexer.lineno += newlines
        self._checkstmt( token )
    
    def _preprocess( self, text ):
        return text

    def _lexanalysis( self, t ):
        if self.directive_scan and self.directive_scan[-1][1] == t.type :
            self.directive_scan.pop(-1)
        elif t.type in ['MEDIA_SYM', 'ATKEYWORD', 'PAGE_SYM'] :
            self.directive_scan.append( (t.type, 'OPENBRACE') )
        elif t.type in self.directives :
            self.directive_scan.append( (t.type, 'SEMICOLON') )

    def _inselector( self, t ) :
        data, pos = self.lexer.lexdata, self.lexer.lexpos
        if self.directive_scan and self.directive_scan[-1][0] == 'EXTEND_SYM' :
            return True
        elif self.directive_scan == [] :
            m = re.search( r';|([^\$]\{)|^\{|\}', data[pos:] )
            return True if m and m.group()[0] not in ';}' else False
        else :
            return False

    def _inproperty( self, t ):
        data, pos = self.lexer.lexdata, self.lexer.lexpos
        if self.directive_scan == [] :
            m = re.search( r'[^{}]+:', data[pos:] )
            return True if m else False
        else :
            return False

    ## --------------- Interface methods ------------------------------

    def __init__( self, error_func=None, conf={}, filename=u'', ):
        """ Create a new Lexer.
        error_func :
            An error function. Will be called with an error message, line
            and column as arguments, in case of an error during lexing.
        """
        self.error_func = error_func
        self.filename = filename
        self.conf = conf
        # Context based lexical analysis
        self.directive_scan = []
        self.propprefix_scan = []

    def build( self, **kwargs ) :
        """ Builds the lexer from the specification. Must be called after the
        lexer object is created. 
            
        This method exists separately, because the PLY manual warns against
        calling lex.lex inside __init__"""
        self.lexer = ply.lex.lex(
                        module=self,
                        reflags=re.UNICODE | re.IGNORECASE,
                        **kwargs
                     )

    def reset_lineno( self ) :
        """ Resets the internal line number counter of the lexer."""
        self.lexer.lineno = 1

    def input( self, text ) :
        """`text` to tokenise"""
        text = self._preprocess( text )
        self.lexer.input( text )
    
    def token( self ) :
        """Get the next token"""
        tok = self.lexer.token()
        return tok 

    # States
    states = (
               ( 'cdata', 'exclusive' ),
               ( 'statement', 'exclusive' ),
               ( 'cssblock', 'exclusive' ),
             )

    ## Tokens recognized by the TSSLexer
    directives = ( 'CHARSET_SYM', 'IMPORT_SYM', 'NAMESPACE_SYM', 'PAGE_SYM',
                   'EXTEND_SYM', 'MEDIA_SYM', 'FONT_FACE_SYM', 'ATKEYWORD' )
    tokens = (
        # Sufffix
        'IMPORTANT_SYM',

        # Comments
        'CDO', 'CDC', 'CDATATEXT', 'S', 'COMMENT',

        # CSS Expressions
        'IDENT', 'URI', 'FUNCTION',

        # Selector Combinator
        'SEL_GT', 'SEL_PLUS', 'SEL_TILDA',
        # Selector tokens
        'SEL_IDENT', 'SEL_STRING', 'SEL_HASH', 'SEL_STAR', 'SEL_COLON', 'DOT',
        # Selector attributes
        'SEL_EQUAL', 'INCLUDES', 'DASHMATCH', 'PREFIXMATCH', 'SUFFIXMATCH',
        'SUBSTRINGMATCH',

        # Literals
        'PAGE_MARGIN_SYM', 'STRING', 'NUMBER', 'DIMENSION', 'UNICODERANGE',
        'HASH', 'QMARK', 'AMPERSAND', 

        # Multi character token 
        'AND', 'OR',

        # Single character token 
        'COMMA', 'EQUAL', 'COLON', 'SEMICOLON',
        'PREFIXSTAR',
        'PLUS', 'MINUS', 'STAR', 'FWDSLASH', 'GT', 'LT',
        'OPENBRACE', 'CLOSEBRACE', 'OPENSQR', 'CLOSESQR',
        'OPENPARAN', 'CLOSEPARAN',

        # Extension tokens
        'EXTN_EXPR', 'EXTN_STATEMENT', 'EXTN_VAR', 'SEL_EXTN_VAR',
        #'PERCENT', 'FUNCTIONSTART', 'FUNCTIONBODY',
        #'IFCONTROL','ELIFCONTROL',  'ELSECONTROL',
        #'FORCONTROL', 'WHILECONTROL',
    ) + directives

    # CSS3 tokens

    hexnum   = r'[0-9a-f]'
    tabspace = r' \t'
    ws       = tabspace + '\r\n\f'
    nl       = r'\n|\r\n|\r|\f'

    spac     = r'[%s]*' % tabspace
    space    = r'[%s]+' % tabspace
    wspac    = r'[%s]*' % ws
    wspace   = r'[%s]+' % ws

    num		 = r'([0-9]*\.)?[0-9]+'
    nonascii = r'[\200-\377]'
    uni      = r'\B\d\D\s\S\w\W'
    unicode_ = r'(\\[0-9a-f]{1,6}[ \t\r\n\f]?)'
    escape	 = unicode_ + r'|' r'(\\[ -~\200-\377])'
    nmstart	 = r'[a-z_]'     r'|' + nonascii + r'|' + escape
    nmchar	 = r'[a-z0-9_-]' r'|' + nonascii + r'|' + escape
    #string1 = r'("([\t !\#$%&(-~]|\\' + nl+ r"|'|" + nonascii + r'|' + escape + r')*")'
    #string2 = r"('([\t !\#$%&(-~]|\\" + nl+ r'|"|' + nonascii + r"|" + escape + r")*')"
    #string	 = r'(' + string1 + r'|' + string2 + r')'
    string	 = r"(\"[^\"]*\")|('[^']*')"
    ident	 = r'[-]?(' + nmstart + r')(' + nmchar + r')*'
    name	 = r'(' + nmchar + r')+'
    url		 = r'([!\#$%&*-~]|' + nonascii + r'|' + escape +r')*'
    range_   = r'\?{1,6}|[0-9a-f](\?{0,5}|[0-9a-f](\?{0,4}|' + \
                  r'[0-9a-f](\?{0,3}|[0-9a-f](\?{0,2}|[0-9a-f](\??|[0-9a-f])))))'

    pagemr   = r'@(page|top-left-corner|top-left|top-center|top-right-corner' + \
                 '|top-right|bottom-left-corner|bottom-left|bottom-center' + \
                 '|bottom-right-corner|bottom-right|left-top' + \
                 '|left-middle|right-bottom|right-top|right-middle' + \
                 '|right-bottom)' + wspac

    @TOKEN( wspace )
    def t_S( self, t ):
        self._incrlineno( t )
        return t

    def t_COMMENT( self, t ):
        r'\/\*[^*]*\*+([^/][^*]*\*+)*\/'
        self._incrlineno( t )
        return t

    @TOKEN( r'@charset' + wspac )
    def t_CHARSET_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'@import' + wspac )
    def t_IMPORT_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'@namespace' + wspac )
    def t_NAMESPACE_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'@media' + wspac )
    def t_MEDIA_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'@font-face' + wspac )
    def t_FONT_FACE_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'@page' + wspac )
    def t_PAGE_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'@extend' + wspac )
    def t_EXTEND_SYM( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( pagemr )
    def t_PAGE_MARGIN_SYM( self, t ):
        self._incrlineno( t )
        return t

    # Gotcha : Browser specific @-rules
    @TOKEN( r'@' + ident + wspac )
    def t_ATKEYWORD( self, t ) :
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'!' + wspac + 'important' + wspac )
    def t_IMPORTANT_SYM( self, t ) :
        self._incrlineno( t )
        return t

    def t_CDO( self, t ):
        r'<!--'
        t.lexer.push_state( 'cdata' )
        return t

    # Gotcha : Confirmance issue : urls are not comfirming to string format
    #@TOKEN( r'url\(' + wspac + string + wspac + r'\)' )
    @TOKEN( r'url\([^)]*\)' )
    def t_URI( self, t ) :
        self._incrlineno( t )
        return t

    @TOKEN( r'~=' + wspac )
    def t_INCLUDES( self, t ) :
        self._incrlineno( t )
        t.value = (INCLUDES, t.value)
        return t

    @TOKEN( r'\|=' + wspac )
    def t_DASHMATCH( self, t ) :
        self._incrlineno( t )
        t.value = (DASHMATCH, t.value)
        return t

    @TOKEN( r'\^=' + wspac )
    def t_PREFIXMATCH( self, t ) :
        self._incrlineno( t )
        t.value = (PREFIXMATCH, t.value)
        return t

    @TOKEN( r'\$=' + wspac )
    def t_SUFFIXMATCH( self, t ) :
        self._incrlineno( t )
        t.value = (SUFFIXMATCH, t.value)
        return t

    @TOKEN( r'\*=' + wspac )
    def t_SUBSTRINGMATCH( self, t ) :
        self._incrlineno( t )
        t.value = (SUBSTRINGMATCH, t.value)
        return t

    rehex = re.compile( r'#([0-9a-zA-Z]{3}|[0-9a-zA-Z]{6})' )
    @TOKEN( r'\#' + name )
    def t_HASH( self, t ) :
        if self._inselector(t) :
            t.type = 'SEL_HASH'
        elif self.rehex.match( t.value ) == None :
            assert 'Must be a hexadecimal number'
        t.value = (HASH, t.value)
        return t

    @TOKEN( num + r'em' )
    def t_EMS( self, t ) :
        t.type = 'DIMENSION'
        t.value = (EMS, t.value)
        return t

    @TOKEN( num + r'ex' )
    def t_EXS( self, t ) :
        t.type = 'DIMENSION'
        t.value = (EXS, t.value)
        return t

    @TOKEN( num + r'px' )
    def t_LENGTH_PX( self, t ) :
        t.type = 'DIMENSION'
        t.value = (LENGTHPX, t.value)
        return t

    @TOKEN( num + r'cm' )
    def t_LENGTH_CM( self, t ) :
        t.type = 'DIMENSION'
        t.value = (LENGTHCM, t.value)
        return t

    @TOKEN( num + r'mm' )
    def t_LENGTH_MM( self, t ) :
        t.type = 'DIMENSION'
        t.value = (LENGTHMM, t.value)
        return t

    @TOKEN( num + r'in' )
    def t_LENGTH_IN( self, t ) :
        t.type = 'DIMENSION'
        t.value = (LENGTHIN, t.value)
        return t

    @TOKEN( num + r'pt' )
    def t_LENGTH_PT( self, t ) :
        t.type = 'DIMENSION'
        t.value = (LENGTHPT, t.value)
        return t

    @TOKEN( num + r'pc' )
    def t_LENGTH_PC( self, t ) :
        t.type = 'DIMENSION'
        t.value = (LENGTHPC, t.value)
        return t

    @TOKEN( num + r'deg' )
    def t_ANGLE_DEG( self, t ) :
        t.type = 'DIMENSION'
        t.value = (ANGLEDEG, t.value)
        return t

    @TOKEN( num + r'rad' )
    def t_ANGLE_RAD( self, t ) :
        t.type = 'DIMENSION'
        t.value = (ANGLERAD, t.value)
        return t

    @TOKEN( num + r'grad' )
    def t_ANGLE_GRAD( self, t ) :
        t.type = 'DIMENSION'
        t.value = (ANGLEGRAD, t.value)
        return t

    @TOKEN( num + r'ms' )
    def t_TIME_MS( self, t ) :
        t.type = 'DIMENSION'
        t.value = (TIMEMS, t.value)
        return t

    @TOKEN( num + r's' )
    def t_TIME_S( self, t ) :
        t.type = 'DIMENSION'
        t.value = (TIMES, t.value)
        return t

    @TOKEN( num + r'Hz' )
    def t_FREQ_HZ( self, t ) :
        t.type = 'DIMENSION'
        t.value = (FREQHZ, t.value)
        return t

    @TOKEN( num + r'kHz' )
    def t_FREQ_KHZ( self, t ) :
        t.type = 'DIMENSION'
        t.value = (FREQKHZ, t.value)
        return t

    @TOKEN( num + r'%' )
    def t_PERCENTAGE( self, t ) :
        t.type = 'DIMENSION'
        t.value = (PERCENTAGE, t.value)
        return t

    @TOKEN( num )
    def t_NUMBER( self, t ) :
        t.value = (NUMBER, t.value)
        return t

    @TOKEN( string )
    def t_STRING( self, t ) :
        self._incrlineno( t )
        if self._inselector(t) : t.type = 'SEL_STRING'
        return t

    @TOKEN( '%s(\.%s)*\(%s' % (ident, ident, wspac) )
    def t_FUNCTION( self, t ) : 
        return t

    @TOKEN( ident )
    def t_IDENT( self, t ) :
        if self._inselector(t) : t.type = 'SEL_IDENT'
        return t

    @TOKEN( r'U\+%s{1,6}-%s{1,6}' % (hexnum, hexnum) )
    def t_UNICODERANGE_S( self, t ) : 
        t.type = 'UNICODERANGE'
        t.value = t.value
        return t

    @TOKEN( r'U\+' + range_ )
    def t_UNICODERANGE_C( self, t ) : 
        t.type = 'UNICODERANGE'
        t.value = t.value
        return t

    @TOKEN( r'\$\{[^}]*\}' + wspac )
    def t_EXTN_EXPR( self, t ) :
        obraces = t.value.count('{') > 1
        lexdata, lexpos = self.lexer.lexdata, self.lexer.lexpos
        txtlen = len(lexdata)
        if obraces > 1 :
            while (lexpos < txtlen) and obraces :
                if lexdata[lexpos] == '{' : obraces += 1
                elif lexdata[lexpos] == '}' : obraces -= 1
                t.value += lexdata[lexpos]
                lexpos += 1
            self.lexer.lexpos = lexpos
        self._incrlineno( t )
        return t

    @TOKEN( r'^[ \t]*\$[^\r\n\f]+;' + wspac )
    def t_EXTN_STATEMENT( self, t ) :
        self._incrlineno( t )
        return t

    @TOKEN( r'[ \t]*\$[^\r\n\f]+;' + wspac )
    def t_statement_EXTN_STATEMENT( self, t ) :
        self._incrlineno( t )
        t.lexer.pop_state()
        return t

    @TOKEN( r'\$[a-zA-Z][a-zA-Z0-9_]*' + wspac )
    def t_EXTN_VAR( self, t ) :
        if self._inselector(t) : t.type = 'SEL_EXTN_VAR'
        return t

    @TOKEN( r'\+' + wspac )
    def t_PLUS( self, t ):
        self._incrlineno( t )
        if self._inselector(t) : t.type = 'SEL_PLUS'
        t.value = (PLUS, t.value)
        return t

    @TOKEN( r'-' + wspac )
    def t_MINUS( self, t ):
        self._incrlineno( t )
        t.value = (MINUS, t.value)
        return t

    @TOKEN( r'\*' + wspac )
    def t_STAR( self, t ):
        self._incrlineno( t )
        if self._inselector( t ) :
            t.type = 'SEL_STAR'
        elif self._inproperty( t ) :
            t.type = 'PREFIXSTAR'
        t.value = (STAR, t.value)
        return t

    @TOKEN( r'\/' + wspac )
    def t_FWDSLASH( self, t ):
        self._incrlineno( t )
        t.value = (FWDSLASH, t.value)
        return t

    @TOKEN( r'%' + wspac )
    def t_PERCENT( self, t ):
        self._incrlineno( t )
        t.value = (PERCENT, t.value)
        return t

    @TOKEN( r'=' + wspac )
    def t_EQUAL( self, t ):
        self._incrlineno( t )
        if self._inselector(t) : t.type = 'SEL_EQUAL'
        t.value = (EQUAL, t.value)
        return t

    @TOKEN( r'>' + wspac )
    def t_GT( self, t ):
        self._incrlineno( t )
        if self._inselector(t) : t.type = 'SEL_GT'
        t.value = (GT, t.value)
        return t

    @TOKEN( r'<' + wspac )
    def t_LT( self, t ):
        self._incrlineno( t )
        t.value = (LT, t.value)
        return t

    @TOKEN( r'~' + wspac )
    def t_TILDA( self, t ):
        self._incrlineno( t )
        t.type = 'SEL_TILDA'
        t.value = (TILDA, t.value)
        return t

    @TOKEN( r'&&' + wspac )
    def t_AND( self, t ):
        self._incrlineno( t )
        t.value = (AND, t.value)
        return t

    @TOKEN( r'\|\|' + wspac )
    def t_OR( self, t ):
        self._incrlineno( t )
        t.value = (OR, t.value)
        return t

    @TOKEN( r'\?' + wspac )
    def t_QMARK( self, t ):
        self._incrlineno( t )
        t.value = (QMARK, t.value)
        return t

    @TOKEN( r',' + wspac )
    def t_COMMA( self, t ):
        self._incrlineno( t )
        t.value = (COMMA, t.value)
        return t

    @TOKEN( r':' + wspac )
    def t_COLON( self, t ):
        self._incrlineno( t )
        if self._inselector(t) : t.type = 'SEL_COLON'
        t.value = (COLON, t.value)
        return t

    @TOKEN( r'\.' + wspac )
    def t_DOT( self, t ):
        self._incrlineno( t )
        t.value = (DOT, t.value)
        return t

    @TOKEN( r';' + wspac )
    def t_SEMICOLON( self, t ):
        self._incrlineno( t )
        self._lexanalysis(t)
        return t

    @TOKEN( r'\{' )
    def t_OPENBRACE( self, t ):
        self._lexanalysis(t)
        return t

    @TOKEN( r'\}' )
    def t_CLOSEBRACE( self, t ):
        return t

    @TOKEN( r'-->' + wspac )
    def t_cdata_CDC( self, t ) :
        t.lexer.pop_state()
        return t

    def t_cdata_CDATATEXT( self, t ):           # <--- `cdata` state
        r'(.|[\r\n\f])+?(?=-->)'
        self._incrlineno( t )
        return t

    def t_cssblock_FUNCTIONSTART( self, t ):
        r'@def'
        return t

    def t_cssblock( self, t ):
        r'.*@end'
        t.lexer.pop_state()
        return t

    t_OPENSQR    = r'\['
    t_CLOSESQR   = r'\]'
    t_OPENPARAN  = r'\('
    t_CLOSEPARAN = r'\)'

    #---- Unused TOKENS

    @TOKEN( r'&' + wspac )
    def t_AMPERSAND( self, t ):
        self._incrlineno( t )
        t.value = (AMPERSAND, t.value)
        return t

    def t_FUNCTIONSTART( self, t ) :
        r'@def'
        self._incrlineno( t )
        t.lexer.push_state('cssblock')
        return t

    def t_IFCONTROL( self, t ) :
        r'@if.*(?!\{[\n\r])\{'
        self._incrlineno( t )
        t.lexer.push_state('cssblock')
        return t

    def t_ELIFCONTROL( self, t ) :
        r'@elif.*(?!\{[\n\r])\{'
        self._incrlineno( t )
        t.lexer.push_state('cssblock')
        return t

    def t_ELSECONTROL( self, t ) :
        r'@else.*(?!\{[\n\r])\{'
        self._incrlineno( t )
        t.lexer.push_state('cssblock')
        return t

    def t_FORCONTROL( self, t ) :
        r'@for.*(?!\{[\n\r])\{'
        self._incrlineno( t )
        t.lexer.push_state('cssblock')
        return t

    def t_WHILECONTROL( self, t ) :
        r'@while.*(?!\{[\n\r])\{'
        self._incrlineno( t )
        t.lexer.push_state('cssblock')
        return t

    def t_error( self, t ):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)

    def t_cdata_error( self, t ):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)

    def t_cssblock_error( self, t ):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)

    def t_statement_error( self, t ):
        msg = 'Illegal character %s' % repr(t.value[0])
        self._error(msg, t)


def _fetchtoken( tsslex, stats ) :
    tok = tsslex.token()
    if tok :
        val = tok.value[1] if isinstance(tok.value, tuple) else tok.value
        print "- %20r " % val,
        print tok.type, tok.lineno, tok.lexpos
        stats.setdefault( tok.type, [] ).append( tok.value )
    return tok

if __name__ == "__main__":
    def errfoo( lex, msg, a, b ) :
        print msg, a, b
        sys.exit()
    
    if len(sys.argv) > 1 :
        stats = {}
        for f in sys.argv[1:] :
            print "Lexing file %r ..." % f
            tsslex = TSSLexer( errfoo, filename=f )
            tsslex.build()
            tsslex.input( codecs.open(f, encoding='utf-8-sig').read() )
            tok = _fetchtoken( tsslex, stats )
            while tok :
                tok = _fetchtoken( tsslex, stats )
