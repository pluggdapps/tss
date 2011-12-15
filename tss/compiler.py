# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

import imp, os, codecs
from   os.path            import isfile, isdir, basename, join, dirname
from   hashlib            import sha1

from   tss.parser         import TSSParser
from   tss.codegen        import InstrGen
from   tss.runtime        import StackMachine, Namespace

class Compiler( object ):
    _memcache = {}

    def __init__( self,
                  tssloc=None,
                  tsstext=None,
                  # Template options
                  tssconfig={},
                  # TSSParser options
                  tssparser=None,
                  # InstrGen options
                  igen=None,
                ):
        # Source TSS
        if isinstance( tssloc, StyleLookup ) :
            self.tsslookup = tssloc
        elif tssloc or tsstext :
            self.tsslookup = StyleLookup(
                tssloc=tssloc, tsstext=tsstext, tssconfig=tssconfig
            )
        else :
            raise Exception( 'To compile, provide a valid tss / css source' )
        self.tssfile = self.tsslookup.tssfile
        self.pyfile = self.tsslookup.pyfile
        self.tssconfig = tssconfig
        # Parser phase
        self.tssparser = tssparser or TSSParser( tssconfig=self.tssconfig )
        # Instruction generation phase
        self.igen = igen or InstrGen( self, tssconfig=self.tssconfig )

    def __call__(self, tssloc=None, tsstext=None, tssconfig={}, tssparser=None):
        tssconfig = tssconfig or self.tssconfig
        tssparser = tssparser or self.tssparser
        return Compiler( tssloc=tssloc, tsstext=tsstext,
                          tssconfig=tssconfig, tssparser=tssparser
                        )

    def exectss( self, code=None, context={} ):
        """Execute the template code (python compiled) under module's context
        `module`.
        """
        # Stack machine
        _m  = StackMachine( self.tssfile, self, tssconfig=self.tssconfig )
        # Module instance for the tss file
        module = imp.new_module( self.modulename )
        module.__dict__.update({
            self.igen.machname : _m,
        })
        module.__dict__.update( context )
        # Load tss translated python code
        code = code or self.tss2code()
        # Execute the code in module's context
        exec code in module.__dict__, module.__dict__
        return module

    def tss2code( self ):
        """Code loading involves, picking up the intermediate python file from
        the cache (if disk persistence is enabled and the file is available)
        or, generate afresh using `igen` Instruction Generator.
        """
        code = self._memcache.get( self.tsslookup.hashkey, None 
               ) if self.tssconfig['devmod'] == False else None
        if code : return code
        pytext = self.tsslookup.pytext
        if pytext :
            tsshash = None
            code = compile( pytext, self.tssfile, 'exec' )
        else :
            pytext = self.topy( tsshash=self.tsslookup.tsshash )
            self.tsslookup.pytext = pytext
            code = compile( pytext, self.tssfile, 'exec' )

        if self.tssconfig['memcache'] :
            self._memcache.setdefault( self.tsslookup.hashkey, code )
        return code

    def toast( self ):
        tsstext = self.tsslookup.tsstext
        tu = self.tssparser.parse( tsstext, tssfile=self.tssfile )
        return tu

    def topy( self, *args, **kwargs ):
        encoding = self.tssconfig['input_encoding']
        tu = self.toast()
        if tu :
            tu.validate()
            tu.headpass1( self.igen )                   # Head pass, phase 1
            tu.headpass2( self.igen )                   # Head pass, phase 2
            tu.generate( self.igen, *args, **kwargs )   # Generation
            tu.tailpass( self.igen )                    # Tail pass
            return self.igen.codetext()
        else :
            return None

    modulename = property( lambda s : basename(s.tssfile).split('.',1)[0] )


class StyleLookup( object ) :
    TSSCONFIG = [ 'directories', 'module_directory', 'devmod' ]
    def __init__( self, tssloc=None, tsstext=None, tssconfig={} ):
        [ setattr( self, k, tssconfig[k] ) for k in self.TSSCONFIG ]
        self.tssconfig = tssconfig
        self.encoding = tssconfig['input_encoding']
        self.tssloc, self._tsstext = tssloc, tsstext
        self._tsshash, self._pytext = None, None
        if self.tssloc :
            self.tssfile = self._locatetss( self.tssloc, self.directories )
            self.pyfile = self.computepyfile( tssloc, tssconfig )
        elif self._tsstext :
            self.tssfile = '<Source provided as raw text>'
            self.pyfile = None
        else :
            raise Exception( 'Invalid tss source !!' )

    def _gettsstext( self ):
        if self._tsstext == None :
            self._tsstext = codecs.open( self.tssfile, encoding=self.encoding ).read()
        return self._tsstext

    def _getpytext( self ):
        if self.devmod :
            return None
        elif self.pyfile and isfile(self.pyfile) and self._pytext == None :
            self._pytext = codecs.open( self.pyfile, encoding=self.encoding ).read()
        return self._pytext

    def _setpytext( self, pytext ):
        if self.pyfile :
            d = dirname(self.pyfile)
            os.makedirs(d) if not isdir(d) else None
            codecs.open( self.pyfile, mode='w', encoding=self.encoding ).write(pytext)
            return len(pytext)
        return None

    def _gettsshash( self ):
        if self._tsshash == None and self._tsstext :
            self._tsshash = sha1( self._tsstext ).hexdigest()
        return self._tsshash

    def _gethashkey( self ):
        return self.tsshash if self.tssconfig['text_as_hashkey'] else self.tssfile

    def _locatetss( self, tssloc, dirs ):
        """TODO : can reordering the sequence of tssloc interpretation improve
        performance ?"""
        # If tssloc is relative to one of the template directories
        files = filter( lambda f : isfile(f), [ join(d, tssloc) for d in dirs ])
        if files : return files[0]

        # If tssloc is provided in asset specification format
        try :
            mod, loc = tssloc.split(':', 1)
            _file, path, _descr = imp.find_module( mod )
            tssfile = join( path.rstrip(os.sep), loc )
            return tssfile
        except :
            return None

        raise Exception( 'Error locating tss file %r' % tssloc )

    def computepyfile( self, tssloc, tssconfig ) :
        """Plainly compute the intermediate file, whether it exists or not is
        immaterial.
        """
        module_directory = tssconfig['module_directory']
        if module_directory :
            tssloc = tssloc[1:] if tssloc.startswith('/') else tssloc
            pyfile = join( module_directory, tssloc+'.py' )
        else :
            pyfile = None
        return pyfile

    tsstext = property( _gettsstext )
    pytext  = property( _getpytext, _setpytext )
    tsshash = property( _gettsshash )
    hashkey = property( _gethashkey )


def supermost( module ):
    """Walk through the module inheritance all the way to the parent most
    module, and return the same
    """
    parmod = module.parent
    while parmod : module, parmod = parmod, parmod.parent
    return module

