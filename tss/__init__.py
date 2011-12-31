# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

"""Package code handles following functions,

* Command script APIs for,
  * dump(), regenerate TSS text from its AST, formed by parsing the text.
  * show(), display AST in human readable form.
  * Generate .css from .tss files.
* API for web frameworks to generate CSS files.
* Define package version.
* Default configuration for extension language.
* Normalization function for configuration values.
"""

import codecs
from   os.path       import basename, join, dirname
from   datetime      import datetime as dt

from   tss.utils     import ConfigDict, asbool, parsecsv
from   tss.parser    import TSSParser

__version__ = '0.1dev'

DEFAULT_ENCODING = 'utf-8-sig'
DEVMOD = False

defaultconfig = ConfigDict()
defaultconfig.__doc__ = """Configuration settings for TSS extension language."""
defaultconfig['parse_optimize']    = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "PLY-Lexer-Yacc option. "
                "Set to False when you're modifying the lexer/parser. "
                "Otherwise, changes in the lexer/parser won't be used, "
                "if some lextab.py file exists. When releasing with a stable "
                "version, set to True to save the re-generation of the "
                "lexer/parser table on each run. Also note that, using "
                "python's optimization feature can break this option, refer, "
                "    http://www.dabeaz.com/ply/ply.html#ply_nn38 "
}
defaultconfig['lextab']    = {
    'default' : None,
    'types'   : (str,unicode),
    'help'    : "PLY-Lexer option. "
                "Points to the lex table that's used for optimized mode. Only "
                "if you're modifying the lexer and want some tests to avoid "
                "re-generating the table, make this point to a local lex table "
                "file. "
}
defaultconfig['yacctab']    = {
    'default' : None,
    'types'   : (str,unicode),
    'help'    : "PLY-Yacc option. "
                "Points to the yacc table that's used for optimized mode. Only "
                "if you're modifying the parser, make this point to a local "
                "yacc table file."
}
defaultconfig['strict_undefined']    = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "Boolean to raise exception for undefined context variables. "
                "If set to false, undefined variables will be silently "
                "digested as 'None' string. "
}
defaultconfig['directories']             = {
    'default' : '.',
    'types'   : ('csv', list),
    'help'    : "Comma separated list of directory path to look for "
                "tss files. Default will be current-directory."
}
defaultconfig['module_directory']        = {
    'default' : None,
    'types'   : (str,),
    'help'    : "Directory path telling the compiler where to persist (cache) "
                "intermediate python file."
}
defaultconfig['input_encoding']          = {
    'default' : 'utf-8-sig',
    'types'   : (str,),
    'help'    : "Default input encoding for .tss file."
}
defaultconfig['memcache']                = {
    'default' : True,
    'types'   : (bool,),
    'help'    : "Cache the compiled python code in-memory to avoid "
                "re-compiling .tss to .py file."
}
defaultconfig['text_as_hashkey']         = {
    'default' : False,
    'types'   : (bool,),
    'help'    : "To be used with 'memcache' option, where the cache tag "
                "will be computed using .tss file's text content. This "
                "will have a small performance penalty instead of using "
                "tss filename as key."
}

def normalizeconfig( config ):
    """Convert string representation of config parameters into programmable
    data types. It is assumed that all config parameters are atleast initialized
    with default value.
    """
    config['devmod'] = asbool( config.get('devmod', False) )
    config['parse_optimize'] = asbool( config['parse_optimize'] )
    config['strict_undefined'] = asbool( config['strict_undefined'] )
    config['module_directory'] = config['module_directory'] or None
    config['memcache'] = asbool( config['memcache'] )
    config['text_as_hashkey'] = asbool( config['text_as_hashkey'] )
    try    : config['directories'] = parsecsv( config['directories'] )
    except : pass
    return config

#---- APIs for executing TSS Extension language

class Translator( object ):
    """Translate TSS file(s) to CSS

    ``tssloc``,
        Location of Tayra template file, either as relative directory or as
        asset specification.
    ``tsstext``,
        Tayra template text. It is assumed in unicode format. 
    ``tssconfig``,
        Configuration parameter, will find its way into every object defined by
        the templating engine.
    """
    def __init__( self, tssloc=None, tsstext=None, tssconfig={} ):
        self.tssconfig = dict( defaultconfig.items() )
        self.tssconfig.update( tssconfig )
        self.tssconfig.setdefault( 'devmod', DEVMOD )
        # Initialize plugins
        self.tssloc, self.tsstext = tssloc, tsstext
        self.tssparser = TSSParser( tssconfig=self.tssconfig )

    def __call__( self, entryfn='main', context={} ):
        """Compile, execute and return css text corresponding to this TSS
        document.

        key-word arguments,
        ``entryfn``,
            name of entry function to be called.
        ``context``,
            dictionary of key,value pairs to be used as context for generating
            css text.

        Arguments to main() function can be passed via context variables,
        ``_mainargs`` (a list of positional arguments) and ``_mainkwargs`` a
        dictionary of key-word arguments.

        dictionary object ``context`` will also be available as _tsscontext
        variable.
        """
        from tss.compiler import Compiler
        self.compiler = Compiler( tsstext=self.tsstext,
                                  tssloc=self.tssloc,
                                  tssconfig=self.tssconfig,
                                  tssparser=self.tssparser
                                )
        context['_tsscontext'] = context
        module = self.compiler.exectss( context=context )
        # Fetch parent-most module
        entry = getattr( module, entryfn )
        args = context.get( '_mainargs', [] )
        kwargs = context.get( '_mainkwargs', {} )
        css = entry( *args, **kwargs ) if callable( entry ) else u''
        return css


def tss_cmdline( tssloc, **kwargs ):
    from tss.compiler import Compiler

    tssconfig = dict( defaultconfig.items() )
    # directories, module_directory, devmod
    tssconfig.update( kwargs )

    # Parse command line arguments and configuration
    tssconfig.setdefault('devmod', DEVMOD)
    args = eval( tssconfig.pop( 'args', '[]' ))
    context = tssconfig.pop( 'context', {} )
    context = eval(context) if isinstance(context, basestring) else context
    context.update( _mainargs=args ) if args else None
    debuglevel = tssconfig.pop( 'debuglevel', 0 )
    show = tssconfig.pop( 'show', False )
    dump = tssconfig.pop( 'dump', False )

    # Setup parser
    tssparser = TSSParser( tssconfig=tssconfig, debug=debuglevel )
    comp = Compiler( tssloc=tssloc, tssconfig=tssconfig, tssparser=tssparser )
    pyfile = comp.tssfile+'.py'
    cssfile = basename( comp.tssfile ).rsplit('.', 1)[0] + '.css'
    cssfile = join( dirname(comp.tssfile), cssfile )

    if debuglevel :
        print "AST tree ..."
        tu = comp.toast()
    elif show :
        print "AST tree ..."
        tu = comp.toast()
        tu.show()
    elif dump :
        tu = comp.toast()
        rctext = tu.dump()
        if rctext != codecs.open( comp.tssfile, encoding=comp.encoding ).read() :
            print "Mismatch ..."
        else : print "Success ..."
    else :
        print "Generating py / CSS file ... "
        pytext = comp.topy( tsshash=comp.tsslookup.tsshash ) # pytext in unicode
        # Intermediate file should always be encoded in 'utf-8'
        enc = comp.encoding.rstrip('-sig') # -sig is used to interpret BOM
        codecs.open( pyfile, mode='w', encoding=enc ).write(pytext)

        t = Translator( tssloc=tssloc, tssconfig=tssconfig )
        css = t( context=context )
        codecs.open( cssfile, mode='w', encoding=enc ).write( css )

        # This is for measuring performance
        st = dt.now()
        [ t( context=context ) for i in range(2) ]
        print (dt.now() - st) / 2
