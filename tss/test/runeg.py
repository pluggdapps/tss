#! /usr/bin/env python

import os, sys, codecs, shutil
from   optparse         import OptionParser
from   os.path          import dirname, abspath, join, isdir, basename

from   tss              import Translator

THISDIR = abspath( dirname( __file__ ))

def execute( tssfile ) :
    print "Translating %r ... \n" % tssfile
    tssfile = join( THISDIR, 'egtss', tssfile )
    csstext = Translator( tssloc=tssfile )()
    cssfile = tssfile.rsplit( '.', 1 )[0] + '.css'
    codecs.open( cssfile, mode='w', encoding='utf-8' ).write( csstext )

skipfiles = [ 'any.tss', 'nestedmedia.tss', 'nestedpage.tss' ]
if __name__ == '__main__' :
    files = os.listdir( join( THISDIR, 'egtss' ))
    [ files.remove(f) for f in skipfiles ]
    map( execute, filter( lambda f : f.endswith('.tss'), files ))
