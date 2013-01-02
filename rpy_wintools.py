
# <license/>

import os, os.path, sys, shutil
import rpy_tools


def get_RHOMES():

    # Standard R
    Rhomes = get_RHOMES_inner("R")

    # RStat, commercially packaged R from Random Technologies LLC
    Rhomes.extend( get_RHOMES_inner("RStat") )
   
    if os.environ.get('RHOME', None):
        Rhomes.insert(0, os.environ.get('RHOME', None))
    
    return Rhomes

def get_RHOMES_inner(progname="R"):
    from win32com.shell import shell, shellcon
    program_files = shell.SHGetFolderPath(0,
                                          shellcon.CSIDL_PROGRAM_FILES,
                                          0,
                                          0)

    Rdir = os.path.join(program_files, progname)
    Rhomes = []
    if os.path.exists(Rdir):
        RVersionDirs = os.listdir(Rdir)
        for thisRVersionDir in RVersionDirs:
          BasePath = os.path.join(Rdir, thisRVersionDir)
          DLLPath1 = os.path.join(BasePath, "bin", "R.dll" )
          DLLPath2 = os.path.join(BasePath, "lib", "R.dll" )
          if os.path.exists(DLLPath1) or os.path.exists(DLLPath2):
             Rhomes.append(  BasePath )
    
    return Rhomes

if __name__ == '__main__':
  RHomes = get_RHOMES()
  print "Found", len(RHomes), " R Installations:"
  for path in RHomes:
     print "    ", path
  print
