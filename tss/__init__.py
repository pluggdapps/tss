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

from  tss.utils     import ConfigDict, asboo, parsecsv

__version__ = '0.1dev'

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
    'help'    : "Comma separated list of directory path to look for a "
                "tss files. Default will be current-directory."
}
defaultconfig['input_encoding']          = {
    'default' : 'utf-8',
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
    config['memcache'] = asbool( config['memcache'] )
    config['text_as_hashkey'] = asbool( config['text_as_hashkey'] )
    try    : config['directories'] = parsecsv( config['directories'] )
    except : pass
    return config

#---- APIs for executing TSS Extension language

class Generator( object ):
    """Generate CSS from a TSS

    `tssconfig` parameter will find its way into every object defined
    by language engine.
    """
    def __init__( self, tssloc=None, ttltext=None, ttlconfig={} ):
        ttlconfig = ttlconfig or deepcopy( dict(defaultconfig.items()) )
        # Initialize plugins
        self.ttlconfig = initplugins( ttlconfig, force=ttlconfig['devmod'] )
        self.ttlloc, self.ttltext = ttlloc, ttltext
        self.ttlparser = TTLParser( ttlconfig=self.ttlconfig )

    def __call__( self, entryfn='body', context={} ):
        """Compile, execute and return html text corresponding the template
        document.

        key-word arguments,
        ``entryfn``,
            name of entry function to be called.
        ``context``,
            dictionary of key,value pairs to be used as context for generating
            html document.

        Arguments to body() function can be passed via context variables,
        ``_bodyargs`` (a list of positional arguments) and ``_bodykwargs`` a
        dictionary of key-word arguments.

        dictionary object ``context`` will also be available as _ttlcontext
        variable.
        """
        from tayra.compiler import Compiler
        self.compiler = Compiler( ttltext=self.ttltext,
                                  ttlloc=self.ttlloc,
                                  ttlconfig=self.ttlconfig,
                                  ttlparser=self.ttlparser
                                )
        context['_ttlcontext'] = context
        module = self.compiler.execttl( context=context )
        # Fetch parent-most module
        entry = getattr( module.self, entryfn )
        args = context.get( '_bodyargs', [] )
        kwargs = context.get( '_bodykwargs', {} )
        html = entry( *args, **kwargs ) if callable( entry ) else u''
        return html

def ttl_cmdline( ttlloc, **kwargs ):
    from   tayra.compiler       import Compiler

    ttlconfig = deepcopy( dict( defaultconfig.items() ))
    # directories, module_directory, devmod
    ttlconfig.update( kwargs )
    ttlconfig.setdefault( 'module_directory', dirname( ttlloc ))

    # Parse command line arguments and configuration
    args = eval( ttlconfig.pop( 'args', '[]' ))
    context = ttlconfig.pop( 'context', {} )
    context = eval(context) if isinstance(context, basestring) else context
    context.update( _bodyargs=args ) if args else None
    debuglevel = ttlconfig.pop( 'debuglevel', 0 )
    show = ttlconfig.pop( 'show', False )
    dump = ttlconfig.pop( 'dump', False )
    encoding = ttlconfig['input_encoding']

    # Initialize plugins
    ttlconfig = initplugins( ttlconfig, force=ttlconfig['devmod'] )

    # Setup parser
    ttlparser = TTLParser(
            ttlconfig=ttlconfig, debug=debuglevel )
    comp = Compiler( ttlloc=ttlloc, ttlconfig=ttlconfig, ttlparser=ttlparser )
    pyfile = comp.ttlfile+'.py'
    htmlfile = basename( comp.ttlfile ).rsplit('.', 1)[0] + '.html'
    htmlfile = join( dirname(comp.ttlfile), htmlfile )

    if debuglevel :
        print "AST tree ..."
        tu = comp.toast()
    elif show :
        print "AST tree ..."
        tu = comp.toast()
        tu.show()
    elif dump :
        tu = comp.toast()
        rctext =  tu.dump()
        if rctext != codecs.open( comp.ttlfile, encoding=encoding ).read() :
            print "Mismatch ..."
        else : print "Success ..."
    else :
        print "Generating py / html file ... "
        pytext = comp.topy( ttlhash=comp.ttllookup.ttlhash )
        # Intermediate file should always be encoded in 'utf-8'
        codecs.open(pyfile, mode='w', encoding=DEFAULT_ENCODING).write(pytext)

        ttlconfig.setdefault( 'memcache', True )
        r = Renderer( ttlloc=ttlloc, ttlconfig=ttlconfig )
        html = r( context=context )
        codecs.open( htmlfile, mode='w', encoding=encoding).write( html )

        # This is for measuring performance
        st = dt.now()
        [ r( context=context ) for i in range(2) ]
        print (dt.now() - st) / 2

