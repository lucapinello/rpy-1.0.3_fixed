import os, os.path, sys, re

"""
rpytools_py provides utility functions used for installing or running rpy
"""

if sys.platform=="win32":
  # Windows doesn't define this although it is straightforward...
  def getstatusoutput(cmd):
    """Return (status, output) of executing cmd in a shell."""
    import os
    if os.name in ['nt', 'dos', 'os2'] :
      # use Dos style command shell for NT, DOS and OS/2
      pipe = os.popen(cmd + ' 2>&1', 'r')
    else :
      # use Unix style for all others
      pipe = os.popen('{ ' + cmd + '; } 2>&1', 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text
else:
  from commands import getstatusoutput


def get_R_HOME(force_exec=False):
  """
  Determine the R installation path

  Set force_exec to avoid using the registry.
  """

  # step 1: try using the environment variable
  rhome = os.getenv("R_HOME")
  
  # step 2: (Windows) Try the registry
  if not rhome and sys.platform == 'win32' and not force_exec:
    try: 
      import win32api, win32con
      hkey = win32api.RegOpenKeyEx( win32con.HKEY_LOCAL_MACHINE,
                                    "Software\\R-core\\R",
                                    0, win32con.KEY_QUERY_VALUE )
      # get the base directory
      rhome = win32api.RegQueryValueEx( hkey, "InstallPath" )[0]
      win32api.RegCloseKey( hkey )
    except:
      print "Unable to determine R version from the registry. Trying another method."
      pass  # failover to exec method

  # step 3: Try executing R to find out
  if not rhome or not os.path.exists(rhome):
    if sys.platform == 'win32':
      stat, rhome = getstatusoutput('R RHOME')
    else:
      stat, rhome = getstatusoutput('R RHOME | tail -n 1')
    if stat or len(rhome)<=0:
      raise RuntimeError("Couldn't execute the R interpreter.\n"
                             "Check whether R is in the execution path.")
    
  rhome = rhome.strip()
  return rhome
      
def get_R_VERSION(RHOME=None, force_exec=False):
  """
  Determine the installed version of R.

  Set force_exec=True to avoid using the registry.
  """
  rver = None
  
  # step 1: (Windows) Try the registry
  if (not RHOME) and (sys.platform == 'win32') and (not force_exec):
    try:
      # Use the registry to find where R.dll is
      import win32api, win32con

      hkey = win32api.RegOpenKeyEx( win32con.HKEY_LOCAL_MACHINE,
                                  "Software\\R-core\\R",
                                  0, win32con.KEY_QUERY_VALUE )

      # get the current version
      rver =  win32api.RegQueryValueEx( hkey, "Current Version" )[0]
      win32api.RegCloseKey( hkey )
    except:
      print "Unable to determine R version from the registry." + \
            " Trying another method."
      pass  # failover to exec method

  # step 2: Try executing R to determine the version
  if not rver:
    if (not RHOME) or (not os.path.exists(RHOME)):
      RHOME = get_R_HOME(force_exec)

    rexec = os.path.join(RHOME, 'bin', 'R')
    stat, output = getstatusoutput('"%s" --version' % rexec )
    if stat or len(output)<=0:
      raise RuntimeError("Couldn't execute the R interpreter" +
                         " `%s'.\n" % rexec )
    # edd 05 Apr 2006  version = re.search("R +([0-9]\.[0-9]\.[0-9])", output)
    version = re.search(" +([0-9]+\.[0-9]+\.[0-9]+)", output)
    #version = re.search(" +([0-9]\.[0-9]\.[0-9])", output)
    if not version:
      raise RuntimeError("Couldn't obtain version number from output\n"
                               "of `R --version'.\n")
    rver = version.group(1)
    
  return rver.strip()

def get_R_VERSION_CODE( verstr=None ):
    if verstr is None:
        verstr = get_R_VERSION()
    rmajor,rminor,rpatch=map( lambda x:int(x), verstr.split('.'))
    rver = "%1d%02d%1d" % (rmajor, rminor, rpatch)
    return rver

def get_R_USER():
  RUSER = os.getenv("R_USER")
  if not os.path.exists(str(RUSER)):
    RUSER = os.getenv("HOME")
  if not os.path.exists(str(RUSER)) and sys.platform == 'win32':
    RUSER = os.getenv("HOMEDRIVE") + os.getenv("HOMEPATH")
  if not os.path.exists(str(RUSER)):
    RUSER=os.getcwd()
  return RUSER


def get_PYTHON_DIR():
  ver = "%d.%d" % sys.version_info[0:2]
  try: 
    import win32api, win32con
    hkey = win32api.RegOpenKeyEx(
      win32con.HKEY_LOCAL_MACHINE,
      "Software\\Python\\PythonCore\\%s\\InstallPath" % ver,
      0, win32con.KEY_QUERY_VALUE )
    # get the base directory
    PYTHON_DIR = win32api.RegQueryValueEx( hkey, "")[0]
    win32api.RegCloseKey( hkey )
  except:
    raise RuntimeError("Unable to determine Python install location from the registry")

  if not os.path.exists(PYTHON_DIR):
    raise RuntimeError("Python install location from the registry does not exist: `%s'"
                       % PYTHON_DIR )
    
  return PYTHON_DIR
