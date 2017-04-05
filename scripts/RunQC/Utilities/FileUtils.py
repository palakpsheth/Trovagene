#!/usr/bin/env python
import sys
import glob
import os
		
# Generic test for file or path existence
def exists( path ) :
	if not os.path.exists( path ) : 
		return False , path + " does not exist! "
	else : return True , ""

# Sometimes people will screw up their first demux due to using
# incorrect sample indices or other reasons.  Therefore use their
# lexicographically last Alignment directory	
def AlignmentDirectoryFromBaseCalls( basecalls_dir ) :
	
	alignment_directories = glob.glob( os.path.join( basecalls_dir , "Alignment*" ) )
	
	if len( alignment_directories ) > 0 : return sorted( alignment_directories , reverse=True )[0]
	else : return ""
	

