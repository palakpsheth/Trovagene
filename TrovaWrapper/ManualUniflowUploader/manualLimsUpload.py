import logging
import os
import psutil
import time
import datetime
import urllib
import urllib2
import smtplib
import traceback
import subprocess
import sys
import glob
import shutil
import xml.etree.ElementTree as ET
from configobj import ConfigObj

CONFIG_FILE         = os.path.join( os.path.dirname( os.path.dirname( os.path.realpath(__file__) )) , 'TrovaWrapper_config.ini' )

# load config file
if not os.path.exists( CONFIG_FILE ) :
	msg = str('The TrovaWrapper config.ini file "' + CONFIG_FILE + '" is missing.  Analysis cannot proceed...')
	tputils.LogAndEmail( msg, 4)
	#logging.critical( msg )
	sys.exit()
#Config = ConfigParser.ConfigParser()
Config = ConfigObj(CONFIG_FILE, raise_errors=True)
# load global section
globalOptions = Config['global']

TROVAEMON_ID  = globalOptions['TROVAEMON_ID']
TROVAEMON_PWD = globalOptions['TROVAEMON_PWD']

#UNIFLOW_URL   = 'https://trovagene_dev.uniconnect.com:8100/uniflow' # test
UNIFLOW_URL   = globalOptions['UNIFLOW_URL']

def UploadRunResultsToUniflow( csvResultsFile , csvStatsFile, pdfFitImageFile, flowcellID ) :

	batchID = 'RB' + flowcellID
	
	proc = subprocess.Popen( [ 'curl' , \
		'-F' , 'userId=' + TROVAEMON_ID , \
		'-F' , 'password=' + TROVAEMON_PWD , \
		'-F' , 'stepName=API Result Upload 2' , \
		'-F' , 'batchId=' + batchID , \
		'-F' , 'flowCellID=' + flowcellID , \
		'-F' , 'status=success' , \
		'-F' , 'formNumber=0' , \
		'-F' , 'Submit=true' , \
		'-F' , 'accountId=Trovagene' , \
		'-F' , 'csvResultsFile=@' + csvResultsFile , \
		'-F' , 'csvStatsFile=@' + csvStatsFile , \
		'-F' , 'pdfFitImage=@' + pdfFitImageFile , \
		UNIFLOW_URL ] ,  stdout=subprocess.PIPE , stderr=subprocess.PIPE )
			  
	out, err = proc.communicate()
	both     = out + err
	print both
		
def Usage():
	print "python " + __file__ + " _summary.csv _stats.csv .pdf flowcellID"
	sys.exit(0)
if __name__=="__main__" :
	if len( sys.argv ) < 5 :
		print Usage()
	else :
		summary = sys.argv[1]
		stats = sys.argv[2]
		pdf = sys.argv[3]
		flowcellID  = sys.argv[4]
		UploadRunResultsToUniflow(  summary, stats, pdf , flowcellID )
		
		
		
