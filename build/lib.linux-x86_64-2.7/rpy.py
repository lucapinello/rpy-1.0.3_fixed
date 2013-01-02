#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
#  High level module for managing the lookup of R objects.
#
#  $Id: rpy.py 489 2008-04-16 14:19:47Z warnes $
#
#
from __future__ import nested_scopes

from rpy_options import rpy_options

import rpy_io
import UserDict
import time, os, sys, atexit, glob
import rpy_tools

# If we cannot import Numeric, it should have been detected at
# installation time and RPy should have been compiled properly. So,
# don't complain.
try:
    from numpy import *
    HAS_NUMERIC = 3
except ImportError:
    try:
        from Numeric import *
        HAS_NUMERIC = 1
    except ImportError:
        HAS_NUMERIC = 0
        pass


# Get necessary paths and version information
RHOME=os.environ.get('RHOME',None)
    
if not RHOME:
    if rpy_options['RHOME'] is not None:
        RHOME = rpy_options['RHOME']
    else:
        RHOME = rpy_tools.get_R_HOME()

if rpy_options['RVERSION'] is not None:
    RVERSION = rpy_options['RVERSION']
else:
    RVERSION = rpy_tools.get_R_VERSION(RHOME)

if rpy_options['RVER'] is not None:
    RVER = rpy_options['RVER']
else:
    RVER = rpy_tools.get_R_VERSION_CODE(RVERSION)

if rpy_options['RUSER'] is not None:
    RUSER = rpy_options['RUSER']
else:
    RUSER = rpy_tools.get_R_USER()

VERBOSE=rpy_options['VERBOSE']

if VERBOSE:
    print "RHOME=",RHOME
    print "RVERSION=",RVERSION
    print "RVER=",RVER
    print "RUSER=",RUSER

# Push these into the environment for rpymodule to pick up
os.environ['RPY_RHOME']=RHOME
os.environ['RPY_RVERSION']=RVERSION
os.environ['RPY_RVER']=RVER
os.environ['RPY_RUSER']=RUSER

# Push R_HOME into the environment for the R shared library/DLL to pick up
os.environ['R_HOME']=RHOME

if sys.platform=='win32':
    import win32api
    os.environ['PATH'] += ';' + os.path.join(RHOME,'bin')
    os.environ['PATH'] += ';' + os.path.join(RHOME,'modules')
    os.environ['PATH'] += ';' + os.path.join(RHOME,'lib')

    # Load the R dll using the explicit path
    # First try the bin dir:
    Rlib = os.path.join( RHOME, 'bin', 'R.dll')
    # Then the lib dir:
    if not os.path.exists(Rlib):
        Rlib = os.path.join( RHOME, 'lib', 'R.dll')
    # Otherwise fail out!
    if not os.path.exists(Rlib):
        raise RuntimeError("Unable to locate R.dll within %s" % RHOME)

    if VERBOSE:
        print "Loading the R DLL %s .." % Rlib,
        sys.stdout.flush()
    win32api.LoadLibrary( Rlib )
    if VERBOSE:
        print "Done."
        sys.stdout.flush()


# load the version of rpy that matches the verison of R we're using
if VERBOSE:
    print "Loading Rpy version %s .." % RVER,
    sys.stdout.flush()


try:
  command = "import _rpy%s as _rpy" % RVER
  exec(command)
except Exception, e:
  raise RuntimeError( str(e) + 
      """

      RPy module can not be imported. Please check if your rpy
      installation supports R %s. If you have multiple R versions
      installed, you may need to set RHOME before importing rpy. For
      example:
  
      >>> from rpy_options import set_options
      >>> set_options(RHOME='c:/progra~1/r/rw2011/')
      >>> from rpy import *
      
      """ % RVERSION)

if VERBOSE:
    print "Done."
    sys.stdout.flush()

# Version
from rpy_version import rpy_version

# Symbolic names for conversion modes
TOP_CONVERSION = 4
PROC_CONVERSION = 4
CLASS_CONVERSION = 3
BASIC_CONVERSION = 2
VECTOR_CONVERSION = 1
NO_CONVERSION = 0
NO_DEFAULT = -1

# Wrap a function in safe modes to avoid infinite recursion when
# called from within the conversion system
def with_mode(i, fun):
    def f(*args, **kwds):
        try:
            e = get_default_mode()
            set_default_mode(i)
            return fun(*args, **kwds)
        finally:
            set_default_mode(e)
    return f

# Manage the global mode
def set_default_mode(mode):
    _rpy.set_mode(mode)

def get_default_mode():
    return _rpy.get_mode()

# Three new exceptions
# base exception
RPyException = _rpy.RPy_Exception;

# R <-> Python conversion exception
RPyTypeConversionException = _rpy.RPy_TypeConversionException;

# Exception raised by R
RPyRException = _rpy.RPy_RException

# for backwards compatibility
RException = RPyException

Robj = _rpy.Robj


# I/O setters
set_rpy_output = _rpy.set_output
set_rpy_input = _rpy.set_input
get_rpy_output = _rpy.get_output
get_rpy_input = _rpy.get_input

if sys.platform != 'win32':
    set_rpy_showfiles = _rpy.set_showfiles
    get_rpy_showfiles = _rpy.get_showfiles

# Default I/O to functions in the 'rpy_io' module
if rpy_options['SETUP_WRITE_CONSOLE']:
    set_rpy_output(rpy_io.rpy_output)
else:
    print "\nSkipping initialization of R console *write* support.\n"

if rpy_options['SETUP_READ_CONSOLE']:
    set_rpy_input(rpy_io.rpy_input)
else:
    print "\nSkipping initialization of R console *read* support.\n"

if rpy_options['SETUP_SHOWFILES']:
    if sys.platform != 'win32':
        set_rpy_showfiles(rpy_io.rpy_showfiles)
else:
    print "\nSkipping initialization of R console *file viewer* support\n"    

# Functions for processing events
import threading

r_events = _rpy.r_events
_r_thread = None
_r_events_running = threading.Event()
_r_lock = threading.Lock()

def r_eventloop():
    while _r_events_running.isSet():
        _r_lock.acquire()
        r_events()
        _r_lock.release()
        time.sleep(0.2)

def start_r_eventloop():
    global _r_thread
    
    if _r_thread and _r_thread.isAlive():
        return
    
    _r_thread = threading.Thread(target=r_eventloop)
    _r_thread.setDaemon(1)
    _r_events_running.set()
    _r_thread.start()
    return _r_thread

def stop_r_eventloop():
    _r_events_running.clear()
    if _r_thread:
        _r_thread.join()

if sys.platform != 'win32':
    atexit.register(stop_r_eventloop)
    start_r_eventloop()


# This function unifies the case of results of length one, which RPy
# returns as single values, and results of length greater than one,
# which are lists.
def as_list(obj):
    try:
        obj+[]
        return obj
    except:
        return [obj]


# A special dict to wrap the arguments in safe modes. It would be
# easier with 2.2, subclassing directly from type 'dict'.
class Dict_With_Mode(UserDict.UserDict):
    def __init__(self, initialdata):
        self.data = initialdata
        
    def __setitem__(self, key, value):
        val = with_mode(BASIC_CONVERSION, value)
        if type(key) in [type(''), type(())]:
            self.data[key] = val
        else:
            self.data[with_mode(BASIC_CONVERSION, key)] = val

# Tables for {PROC,CLASS}_CONVERSION modes
class_table = Dict_With_Mode(_rpy.__class_table__)
proc_table = Dict_With_Mode(_rpy.__proc_table__)

# main class
class R:

    def __init__(self):
        if rpy_options['VERBOSE']:
            print "Creating the R object 'r' ..",
            sys.stdout.flush()
        _rpy.r_init(HAS_NUMERIC);
        _rpy.set_mode(NO_DEFAULT)
        
        self.get = _rpy.get_fun('get')  # this must happen before any calls to self or its methods!
        
        self("options(error = expression(NULL))")  # don't abort on errors, just raise them!
                                                   # necessary for non-interactive execution
        self.TRUE = self.__getitem__('T')
        self.FALSE = self.__getitem__('F')
        self.NA = self('NA')
        self.NAN = self('as.double(NA)')
        self.helpfun = with_mode(NO_CONVERSION, self.__getitem__('help'))
        self.help = self.__help__  # override r.help()

        # workaround for plotting bug under win32
        if sys.platform == 'win32':
            self('options(windowsBuffered=FALSE)')

        if rpy_options['VERBOSE']:
            print " Done"
            sys.stdout.flush()
        
    def __getattr__(self, name):
        if name.startswith('__') and name.endswith('__'): return object.__getattr__(name)
        if len(name) > 1 and name[-1] == '_' and name[-2] != '_':
            name = name[:-1]
        name = name.replace('__', '<-')
        name = name.replace('_', '.')
        return self.__getitem__(name)
    
    def __getitem__(self, name):
        # use r's 'get' function here, because the rpy one only handles functions!
        obj = self.__dict__[name] = self.__dict__.get(name, self.get(name)) 
        return obj

    def __call__(self, s):
        return self.eval(self.parse(text=s))

    def __help__(self, *arg, **kw):
        """
        R's help funtion now returns an object of class help that
        must be printed (by R) in order to be rendered.  This
        function forces printing so that the user get the expected
        behavior.
        """
        helpobj = self.helpfun(*arg, **kw)
        self.print_(helpobj)

    def __repr__(self):
        Rver = self.__getitem__('R.version.string')
        return "RPy version %s [%s]" % (rpy_version, Rver)

    def __str__(self):
        return repr(self)

    def __cleanup__(self):
        _rpy.r_cleanup()
        del(self)
    
# main instance
r = R()

# disable the printing of errors from within R, they will be handed by
# passing a fault to python
r.options(show_error_messages=0)

# That's all...

