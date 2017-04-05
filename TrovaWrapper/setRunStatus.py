#!/usr/bin/env python
import os
import sys
import glob
import smtplib
import json
from Keys import Keys as limskeys
# import urllib3.contrib.pyopenssl
# urllib3.contrib.pyopenssl.inject_into_urllib3()
import urllib
import urllib2
from Utilities import TrovapipeUtils as tputils
from configobj import ConfigObj

#read config file and get thresholds
configFile = os.path.realpath( os.path.join( os.path.dirname(__file__), 'TrovaWrapper_config.ini' ) )
Config = ConfigObj(configFile, raise_errors=True)
globalOptions = Config['global']

TROVAEMON_ID  = globalOptions['TROVAEMON_ID']
TROVAEMON_PWD = globalOptions['TROVAEMON_PWD']
UNIFLOW_URL   = globalOptions['UNIFLOW_URL']

#TROVAEMON_ID  = "trovaemon"
#TROVAEMON_PWD = "trovaemon123"
#UNIFLOW_URL   = 'https://trovagene_dev.uniconnect.com:8100/uniflow' # test
#UNIFLOW_URL   = 'https://trovagene.uniconnect.com/uniflow' # production

''' Sets the state of an experiment.  If experiment 
    does not exist it will be created.
'''
def SetUniflowState( flowcellID , state ) :
	
	values = { 
	'userId'     : TROVAEMON_ID, 
	'password'   : TROVAEMON_PWD, 
	'stepName'   : 'Update Run Status', 
	'Submit'     : 'true', 
	'flowcellID' : flowcellID , 
	'status'     : state 
	}
	
	data = urllib.urlencode( values )
	req = urllib2.Request( UNIFLOW_URL , data )
	response = urllib2.urlopen( req )
	response_code = response.getcode()
	if response_code != 200 :
		print "WARNING: response code was not 200 (okay): " + str( response_code )
	else : print "AOK: 200"
	return response_code 

def Usage() :
	print "python setExperimentStatus.py run_id STATE_STRING"
	
''''''''''''''''''''''''
''' Main	
'''''''''''''''''''''
if __name__=="__main__" :

	if len( sys.argv ) != 3 :
		Usage()
	else :
		run_id = sys.argv[1]
		state_string  = sys.argv[2]
		SetUniflowState( run_id , state_string )
