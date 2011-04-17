# vim:tabstop=4:shiftwidth=4:expandtab:autoindent:softtabstop=4
# NOTE: 4 spaces used for indent!!!

"""
Copyright (c) 2011, AppCove, Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or 
without modification, are permitted provided that the 
following conditions are met:

* Redistributions of source code must retain the above 
  copyright notice, this list of conditions and the 
  following disclaimer.

* Redistributions in binary form must reproduce the above 
  copyright notice, this list of conditions and the 
  following disclaimer in the documentation and/or other 
  materials provided with the distribution.

* Neither the name of the IonZoft, Inc. nor the names of 
  its contributors may be used to endorse or promote 
  products derived from this software without specific 
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR 
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING 
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF 
SUCH DAMAGE.

-----------------------------------------------------------
Refactored to work with Python 2.4.4

"""


#TODO: look at Parser.destroy() to break cyclic memory references..  
#      Perhaps destroy it before entering the main workers.

import sys
import os
from optparse import OptionParser

Parser = OptionParser(usage="%prog address port")

# -----------------------------------------------------------------------------
# Global options

Parser.add_option("--DebugLevel", '-d',
    dest    = "DebugLevel",
    action  = "store",
    default = 0,
    type    = "int",
    help    = "Amount of debugging info [0-5]."
    )


# Parse command line
Opt, Arg = Parser.parse_args()

if len(Arg) != 2:
    Parser.error("Command requires 2 arguments (address, port).")
    

Address = Arg[0]

try:
    Port = int(Arg[1])
except ValueError, e:
    Parser.error("port argument: %s" % e.message)


# Enable debugging
import PySrv
PySrv.EnableDEBUG(Opt.DebugLevel)


# -----------------------------------------------------------------------------
if DE:BUG(1, "Starting `Server`: PID %s" % os.getpid())


# Start in enter->debug mode if DE > 0
if DE > 0:
    import pdb
    
    PySrv.Init(Address, Port)
    while 1:
        PySrv.Run()
        pdb.set_trace()

# Start in enter->exit mode
else:
    PySrv.Init(Address, Port)
    PySrv.Run()





