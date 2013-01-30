#! /usr/bin/env python

# -*- coding: utf-8 -*-

# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 R Pratap Chakravarthy

from   argparse             import ArgumentParser
from   os.path              import isfile, join, dirname, basename

import pluggdapps
from   pluggdapps.platform import Pluggdapps
from   pluggdapps.plugin   import ISettings

import tss
from   tss.parser           import TSSParser

def _option_parse() :
    """Parse the options and check whether the semantics are correct."""
    parser = OptionParser(usage="usage: %prog [options] filename")
    parser.add_option( '-o', '--outfile', dest='ofile', default=None,
                       help='Output html file to store translated result' )
    parser.add_option( '-d', action='store_true', dest='dump',
                       help='Dump translation' )
    parser.add_option( '-s', action='store_true', dest='show',
                       help='Show AST parse tree' )
    parser.add_option( '-t', action='store_true', dest='generate',
                       help='Generate python executable' )
    parser.add_option( '-x', action='store_true', dest='execute',
                       help='Executable and generate html' )
    parser.add_option( '-a', dest='args', default='[]',
                       help='Argument to template' )
    parser.add_option( '-c', dest='context', default='{}',
                       help='Context to template' )
    parser.add_option( '-g', dest='debug', default='0',
                       help='Debug level for PLY parser' )
    parser.add_option( '--version', action='store_true', dest='version',
                       help='Version information of the package' )

    options, args   = parser.parse_args()

    return options, args

def main() :
    options, args = _option_parse()


    if options.version :
        print tss.__version__

    elif args and isfile(args[0]) :
        ttlloc = args.pop(0)
        tss.tss_cmdline( ttlloc, _options=options )
    elif int(options.debug) :
        TSSParser( tssconfig={}, debug=int(options.debug) )

def main()
    argparser = mainoptions()
    options = argparser.parse_args()
    pa = Pluggdapps.boot( None )
    
    # Initialize plugins
    setts = {
        'lex_debug'  : int( options.debug ),
        'yacc_debug' : int( options.debug ),
        'debug'      : True,
    }

    compiler = pa.query_plugin( pa, ISettings, 'tsscompiler', settings=setts )
    if options.version :
        print( tss.__version__ )

    elif options.test :
        pass

    elif options.ttllex and options.ttlfile : 
        print( "Lexing file %r ..." % options.ttlfile )
        lexical( pa, options )

    elif options.dump and options.ttlfile :
        print( "Parsing and dumping file %r ..." % options.ttlfile )
        ast = yaccer( pa, options, debuglevel=int(options.debug) )
        dumptext = ast.dump( context=Context() )
        text = open( options.ttlfile, encoding='utf-8-sig' ).read()
        if dumptext != text :
            open( 'dump', 'w' ).write( dumptext )
            open( 'text', 'w' ).write( text )
            assert False
        print( "Dump of AST matches the original text :)")

    elif options.show and options.ttlfile :
        print( "Parsing and describing file %r ..." % options.ttlfile )
        ast = yaccer( pa, options, debuglevel=int(options.debug) )
        ast.show()

    elif options.ttlfile and isfile( options.ttlfile ) :
        print( "Translating file %r ..." % options.ttlfile )
        tayra.translatefile( options.ttlfile, compiler, options )


if __name__ == '__main__' :
    main()
