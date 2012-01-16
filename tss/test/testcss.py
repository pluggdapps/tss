#! /usr/bin/env python

import os, sys, codecs, shutil
from   optparse         import OptionParser
from   os.path          import abspath, join, isdir, basename

from   tss              import tss_cmdline
from   tss.parser       import TSSParser

THISDIR = abspath( '.' )

def test_dump( tu, reftext ):
    dumptext = tu.dump()
    if reftext != dumptext :
        txtlen = len(reftext) if len(reftext) < len(dumptext) else len(dumptext)
        diff = [ i for i in range(txtlen) if reftext[i] != dumptext[i] ]
        off = diff and diff[0] or len(reftext)
        codecs.open('a', mode='w', encoding='utf-8').write(reftext)
        codecs.open('b', mode='w', encoding='utf-8').write(dumptext)
        return False
    else :
        return True

def test_translate( tssloc, options ):
    kwargs = {}
    kwargs.update( plaincss=options.plaincss )
    tss_cmdline( tssloc, **kwargs )
    tsstext = codecs.open(tssloc, encoding='utf-8-sig',).read()
    cssfile = tssloc[:-4]+'.css'
    csstext = codecs.open(cssfile, encoding='utf-8-sig').read()
    rc = csstext == tsstext
    if options.rmonsuccess and rc :
        os.remove(tssloc)
        os.remove(tssloc+'.py')
        os.remove(cssfile)
    return rc

def test_execute( f, options ) :
    print "Testing %r ...\n" % f,
    csstext = codecs.open(f, encoding='utf-8-sig').read()
    tssparser = TSSParser( debug=int(options.debug) )
    tu = tssparser.parse( csstext, debuglevel=int(options.debug) )
    tu.validate()
    rc = None
    if options.show :
        tu.show()
    else :
        if test_dump( tu, csstext ) == False :
            print '(dump failed)'
            rc = 'failure'
        elif test_translate( f, options ) == False :
            print '(translate failed)'
            rc = 'failure'
        else :
            print '(success)'
            rc = 'success'
    if rc == 'failure' : sys.exit(1)
    return rc

def test_samplecss( cssdir, options ) :
    failures = success = total = knownerrors = 0
    for f in os.listdir( cssdir ) :
        f = join( cssdir, f )
        if isdir(f) : continue
        rc = test_execute(f, options)
        #---
        #if isdir( join(cssdir,'t') ) :
        #    shutil.move( f, join(cssdir, 't', basename(f)) )
        #---
        if rc == 'success' : success += 1
        elif rc == 'failure' : failures += 1
        elif rc == 'knownerror' : knownerrors += 1
        total += 1
    print "Success      : %r" % success
    print "Failures     : %r" % failures
    print "KnownErrors  : %r" % knownerrors
    print "Total        : %r" % total

def _option_parse() :
    '''Parse the options and check whether the semantics are correct.'''
    parser = OptionParser(usage="usage: %prog [options] filename")
    parser.add_option( '-d', dest='directory',
                       help='run test on directory' )
    parser.add_option( '-c', action='store_true', dest='plaincss',
                       help='Interpret input text as plain css' )
    parser.add_option( '-r', action='store_true', dest='rmonsuccess',
                       help='remove on success' )
    parser.add_option( '-g', dest='debug', default='0',
                       help='Debug' )
    parser.add_option( '-s', action='store_true', dest='show',
                       help='Show AST parse tree' )

    options, args   = parser.parse_args()

    return options, args

if __name__ == '__main__' :
    options, args = _option_parse()
    if args :
        [ test_execute( abspath(f), options ) for f in args ]
    elif options.directory :
        test_samplecss( abspath(options.directory), options )
