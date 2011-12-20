from   StringIO     import StringIO 
from   tss.runtime  import * 


def main(  ) :  
  _m.pushbuf()
  _m.extend( [u'a', u' ', u'{', u'\n  ', u'color1', u' ', u':', u' ', u'10', u',', u' ', u'20', u';', u'\n  ', u'color2', u' ', u':', u' ', u'10', u'*', u' ', u'20', u';', u'\n  ', u'color3', u' ', u':', u' ', u'10', u' ', u'*', u'expression(', u'20', u',', u'30', u')', u';', u'\n  ', u'color4', u' ', u':', u' ', u'1px', u' ', u'solid', u' ', u'gray', u';', u'\n  ', u'color5', u' ', u':', u' ', u'10', u'+', u'20', u' ', u'*', u'30', u' ', u'-', u'40', u'/', u'50', u';', u'\n  ', u'color6', u' ', u':', u' ', u'(', u'10', u'+', u'20', u')', u' ', u'*', u' ', u'(', u'30', u'-', u'40', u')', u'/', u'50', u';', u'\n  ', u'color7', u' ', u':', u' ', u'-', u'20', u';', u'\n  ', u'color8', u' ', u':', u' ', u'-', u'20', u'*', u'30', u';', u'\n  ', u'color9', u' ', u':', u' ', u'-', u'20', u'*', u'30', u';', u'\n  ', u'color10', u' ', u':', u' ', u'20', u' ', u'-', u'+', u'10', u';', u'\n  ', u'color11', u' ', u':', u' ', u'1px', u' ', u'solid', u' ', u'gray', u',', u' ', u'10px', u' ', u'*', u' ', u'40em', u';', u'\n', u'}', u'\n'] )
  return _m.popbuftext()

# ---- Footer
_tsshash = 'c0ea4c805dc41b374618ee28a7006b315b38aaa9'
_tssfile = './egtss/expr.tss' 