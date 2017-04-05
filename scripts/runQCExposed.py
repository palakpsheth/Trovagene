#!/usr/bin/env python
import sys
from RunQC import runQC as QC

def CheckQual( basecalls_dir ) :

	# writes the run quality report to the experiment root
	# as: RunQuality_runID.csv
	analyzable , message = QC.check_run( basecalls_dir )
	
	print "Is this data analyzable: " + str( analyzable )
	print "Message: " + message
	
def Usage():
	print "python runQCExposed.py /some/path/too/root/Data/Intensities/BaseCalls"

''''''''''''''''''''''''
''' Main	
'''''''''''''''''''''
if __name__=="__main__" :

	if len( sys.argv ) != 2 :
		Usage()
	else :
		basecalls_dir = sys.argv[ 1 ]
		CheckQual( basecalls_dir )
