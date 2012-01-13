# This file is subject to the terms and conditions defined in
# file 'LICENSE', which is part of this source code package.
#       Copyright (c) 2011 SKR Farms (P) LTD.

# -*- coding: utf-8 -*-

from tss.runtime import *

def tss_color( red, blue, green ):
    return STRING_( '#%x%x%x' % (red, blue, green) )

def tss_add( a, b ):
    return NUMBER_( str(a+b) )
