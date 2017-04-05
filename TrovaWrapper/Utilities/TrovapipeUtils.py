#!/usr/bin/env python
import logging
import os, sys
import psutil
import time
import datetime
import urllib
import urllib2
from email.mime.text import MIMEText
sys.path.append( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) )
sys.path.append( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ) )
sys.path.append( os.path.join( os.path.dirname( os.path.dirname( os.path.dirname( os.path.realpath(__file__) ) ) ), 'bin' ) )
from Keys import Keys as limskeys
import smtplib
import traceback
import subprocess
import glob
import shutil
import xml.etree.ElementTree as ET
from configobj import ConfigObj 

# load config file
CONFIG_FILE = os.path.realpath( os.path.join( os.path.dirname( os.path.dirname( __file__) ), "TrovaWrapper_config.ini" ) )
if not os.path.exists( CONFIG_FILE ) :
		msg = str('The TrovaWrapper config.ini file "' + CONFIG_FILE + '" is missing.  Analysis cannot proceed...')
		#LogAndEmail( msg, 4)
		logging.critical( msg )
		sys.exit()
#print "CONFIG_FILE: " + CONFIG_FILE + "\n"
#Config = ConfigParser.ConfigParser()
Config = ConfigObj(CONFIG_FILE, raise_errors=True)
# load global section
#for key, value in Config.iteritems() :
#	print "KEY: " + str(key) + " VALUE: " + str(value) + "\n"
#	if 'global' in str(key):
globalOptions = Config['global']
UNIFLOW_URL   = globalOptions['UNIFLOW_URL']
TROVAEMON_ID  = globalOptions['TROVAEMON_ID']
TROVAEMON_PWD = globalOptions['TROVAEMON_PWD']
MAX_RETRY = globalOptions['MAX_RETRY']

''' Returns a list of paths to MiSeq repositories
'''
def Repositories() :
	
	# get repo info
	repoSection = Config['repos']
	
	repositories = list()
	
	for key, value in repoSection.iteritems():
		if ('repo' in key) and (not value == ''):
			if os.path.exists( value ) :
				repositories.append( os.path.realpath( value ) )
				msg = "Repo identified " + os.path.realpath( value )
				logging.info( msg )
			
	return repositories

def SSRepositories(ConfigObject) :
	
	# load config file
	globalOptions = ConfigObject['global']
	UNIFLOW_URL   = globalOptions['UNIFLOW_URL']
	TROVAEMON_ID  = globalOptions['TROVAEMON_ID']
	TROVAEMON_PWD = globalOptions['TROVAEMON_PWD']
	
	# get repo info
	repoSection = ConfigObject['ss_repos']
	
	repositories = list()
	
	for key, value in repoSection.iteritems():
		if 'all' in key or 'MiSeq' in key or key.startswith('M') and not value == '':
			if not os.path.exists( value ) :
				os.makedirs( value )
			repositories.append( os.path.realpath( value ) )
			msg = "Repo identified " + os.path.realpath( value )
			logging.info( msg )
	
	return repositories

def SSRepositoriesDict(ConfigObject) :
	
	# load config file
	globalOptions = ConfigObject['global']
	UNIFLOW_URL   = globalOptions['UNIFLOW_URL']
	TROVAEMON_ID  = globalOptions['TROVAEMON_ID']
	TROVAEMON_PWD = globalOptions['TROVAEMON_PWD']
	
	# get repo info
	repoSection = ConfigObject['ss_repos']
	
	repositories = {}
	
	for key, value in repoSection.iteritems():
		if 'all' in key or 'MiSeq' in key and not value == '':
			if not os.path.exists( value ) :
				os.makedirs( value )
			repositories[ key ] = ( os.path.realpath( value ) )
			#msg = "Repo identified " + os.path.realpath( value )
			#logging.info( msg )
	
	return repositories

		
''' Deletes the lock file upon normal exit
'''
def CleanUp( LOCK_FILE , APP_NAME ) :
	LogAndEmail('Stopping ' + APP_NAME + ': ' + datetime.datetime.fromtimestamp( time.time() ).strftime( '%Y-%m-%d %H:%M:%S' ) , 0 )
	if os.path.exists( LOCK_FILE ) : os.remove( LOCK_FILE )
	logging.info( 'Complete.\n')

''' Central routing for errors and messages in general
    Priorities:
	0: Lowest, just log the message as info
	1: Low, log the message as info and email bioinformatics
	2: Medium, log the message as error, email bioinformatics
	>=3: High, log the message as critical, email bioinformatics & executive level
'''
def LogAndEmail( message , priority, emailIn=None ) :

	if priority == 0 :
		logging.info( message )
	elif priority > 0 :
		logging.error( message )
		if emailIn is not None:
			Email( message , priority, emailIn)
		else:
			Email( message , priority )
		
''' Email message to bioinfo
'''
def Email( message , priority, emailIn=None ) :
	SILENCE_EMAIL = globalOptions['SILENCE_EMAIL']
	if SILENCE_EMAIL == True or SILENCE_EMAIL.upper() == 'TRUE' : return
	
	msg = MIMEText( message )

	# get email info
	if emailIn is not None:
		emailSection = emailIn
	else:
		emailSection = Config['emails']
	
	emailList = list() 
	
	for key, value in emailSection.iteritems():
		if 'email' in key : 
			emailList.append( value )
	
	send_list = ",".join( emailList )
	
	# use this later to automatically generate tickets?
	#cc  = "support@trovagene.atlassian.net"
	
	status = 'ERROR'
	if 'WARNING' in message.upper():
		status = 'WARNING'
	
	me  = "trovaemon@trovagene.com"
	msg['Subject'] = 'AUTOMATED MESSAGE: ' + status
	msg['From']    = me
	msg['To']      = send_list
	
	s = smtplib.SMTP('localhost') 
	
	# s.set_debuglevel(1) # debug output 2 screen
	
	# if 'Cc' in msg :
		# s.sendmail( msg[ 'From' ] , msg[ 'To' ].split( ',' ) + msg[ 'Cc' ].split( ',' ), msg.as_string() )
	# else :
	
	s.sendmail( msg[ 'From' ] , msg[ 'To' ].split( ',' ) , msg.as_string() )
	s.quit()
	
''' JSON comes back as a complex string, this
    converts to dictionary
	
	ALERT: Exceptions not handled, you must catch
	- work with uniconnect to dev better schema
'''
def ParseJSONOneRun( JSON ) :
	
	tokens1 = JSON.split( '{' )
	tokens2 = tokens1[ 1 ].split( '}' )
	temp = tokens2[ 0 ].replace( '\n' , '' )
	results = dict()
	comma_tokens = temp.split( ',' )
	for token in comma_tokens :
		bits = token.replace( '"' , '' ).split( ':' )
		results[ bits[ 0 ].strip() ] = bits[ 1 ].strip()
	
	return results
	
''' JSON comes back as a complex string, this
    converts to dictionary of dictionaries:
	one per run 
	
	ALERT: Exceptions not handled, you must catch
	- work with uniconnect to dev better schema
'''
def ParseJSONMultipleRuns( JSON ) :
	results = dict()
	temp = dict()
	left_tokens = JSON.split( '{' )
	for left_token in left_tokens :
		if left_token.startswith( '"' ) :
			right_tokens = left_token.split( '}' )
			for right_token in right_tokens :
				groups = right_token.replace( '\n,' , '' ).replace( '])' , '' ).strip().replace( '\n' , '' ).strip().split( ',' )
				temp = {}
				for group in groups :
					items = group.split( '":"' )
					if len( items ) == 2 :
						temp[ items[ 0 ].replace( '"' , '' ).strip() ] = items[ 1 ].replace( '"' , '' ).strip()
				if 'flowcellID' in temp :
					results[ temp[ 'flowcellID' ] ] = temp
	return results
	
''' Uploads CSV results file to uniflow
'''
def UploadRunResultsToUniflow( csvResultsFile , csvStatsFile, pdfFitImageFile, flowcellID, runId=None ) :

	try :
		
		## make review dir if doesnt exist
		#if runId != None:
		#	reviewOut = os.path.join( reviewDir, runId )
		#else:
		#	reviewOut = os.path.join( reviewDir, flowcellID )
		#if not os.path.exists( reviewOut ):
		#	os.makedirs( reviewOut )
	
		## Verify all results files exist and if they do, copy to review dir or raise error
		#results_files = [ str(csvResultsFile) , str(csvStatsFile), str(pdfFitImageFile) ]
		#for resultFile in results_files:
		#	if os.path.exists( str(resultFile) ):
		#		shutil.copy( resultFile , reviewOut )
		#	else:
		#		LogAndEmail( 'ERROR: Missing TrovaPipe output file: ' + str(resultFile), 3 )
		#		sys.exit()
		
		# Push results up to Uniflow
	
		LogAndEmail( 'Uploading TrovaPipe results to Uniflow for flowcellID: ' + flowcellID , 0 )
	
		batchID = 'RB' + flowcellID
		
		proc = subprocess.Popen( [ 'curl' , \
		'-F' , 'userId=' + TROVAEMON_ID , \
		'-F' , 'password=' + TROVAEMON_PWD , \
		#'-F' , 'stepName=API Result Upload 2' , \
		'-F' , 'stepName=Upload Pipeline Results' , \
		'-F' , 'batchId=' + batchID , \
		'-F' , 'flowCellID=' + flowcellID , \
		'-F' , 'status=success' , \
		'-F' , 'formNumber=0' , \
		'-F' , 'Submit=true' , \
		'-F' , 'accountId=Trovagene' , \
		'-F' , 'csvResultsFile=@' + csvResultsFile , \
		'-F' , 'csvStatsFile=@' + csvStatsFile , \
		'-F' , 'pdfFitImage=@' + pdfFitImageFile , \
		'--insecure' , \
		UNIFLOW_URL ] ,  stdout=subprocess.PIPE , stderr=subprocess.PIPE )

		out, err = proc.communicate()
		both = out + err
		
		#LogAndEmail( 'UNIFLOW UPLOAD: ' + str(proc.list2cmdline()) + " RESPONSE: " + str(both), 0)

		if "SYSTEM EXCEPTION" in both or "<span>*1" in both or "couldn't open file" in both or "SSL certificate problem" in both:
			message = "ERROR: An error occurred while trying to upload TrovaPipe results file to UniFlow using curl: " + str(proc) + '\n\t' + 'RETURNED: ' + str(both)
			LogAndEmail( message , 4 )
			sys.exit(1)	
			
	except Exception as detail : # Catch ALL exceptions 
		message = "ERROR: An error occurred while trying to upload TrovaPipe results for flowcellID " + flowcellID + " to UniFlow using curl: " + str(detail) + ".\n\tMESSAGE: " + traceback.format_exc()
		LogAndEmail( message  , 4 )
	
''' Gets the state of the run from UNIFlow
    by way of a RESTful API
	- if parsing error return None
	- if exists return state, if not create and set/return
'''	
def GetUNIFlowState( flowcellID ) :
 
	values = { 
	'userId'     : globalOptions['TROVAEMON_ID'],
	'password'   : globalOptions['TROVAEMON_PWD'],
	'stepName'   : 'Query Run Status', 
	'Submit'     : 'true', 
	'flowcellID' : flowcellID 
	}
	
	data     = urllib.urlencode( values )
	request  = urllib2.Request( globalOptions['UNIFLOW_URL'] , data )
	response = urllib2.urlopen( request )

	JSON     = response.read()
		
	results = dict()
	
	try :
		results = ParseJSONOneRun( JSON )
	except Exception as detail : # Catch ALL exceptions
		message = "ERROR: UNIFlow Error - Unable to parse JSON when querying state of flowcellID: " + flowcellID + " " + str( detail ) + " " + traceback.format_exc()
		LogAndEmail( message , 3 )
		return None
		
	if 'status' not in results or 'flowcellID' not in results :
		message = "ERROR: UNIFlow Error - Unable to find status or flowcellID results when querying state of run: " + flowcellID
		LogAndEmail( message , 3 )
		return None
	
	else :
	
		if results[ 'status' ] == 'NONE' and results[ 'flowcellID' ] == 'NGS_RUN_DOES_NOT_EXIST' :
			response_code = SetUNIFlowState( flowcellID , limskeys.NGS_RUN_PENDING )
			if response_code == 200 : return limskeys.NGS_RUN_PENDING
			else :
				message = "ERROR: UNIFlow Error - response code was not 200 (not okay) when setting state of run: " + \
				flowcellID + " to " + limskeys.NGS_RUN_PENDING
				LogAndEmail( message , 3 )				
				return None
		else :
			return results[ 'status' ]
	
''' Returns flowcellID and metadata for runs
    with the specified status
'''
def QueryRunsByStatus( status, URL=None ) :
	
	values = {
	'userId'     : globalOptions['TROVAEMON_ID'],
	'password'   : globalOptions['TROVAEMON_PWD'],
	'stepName': 'Query Runs By Status',
	'Submit'  : 'true', 
	'status'  : status
	}
	
	url_encoded_values = urllib.urlencode( values )
	if URL is not None:
		request            = urllib2.Request( URL , url_encoded_values )
	else:
		request            = urllib2.Request( globalOptions['UNIFLOW_URL'] , url_encoded_values )
	retryCount = 0
	while retryCount <= MAX_RETRY:
		try:
			response           = urllib2.urlopen( request )
			break
		except:
			if retryCount < MAX_RETRY:
				retryCount = retryCount + 1
				time.sleep(10)
			else:
				raise
	
	JSON               = response.read()
	
	if "SYSTEM EXCEPTION" in JSON :
		message = "ERROR: Uniflow Error - Error when attempting to query UNIFlow stepName: Query Runs By Status.\nUNIFlow output: " + JSON
		LogAndEmail( message , 4 )
		return None
		
	try :
		results = ParseJSONMultipleRuns( JSON )
		return results
	except Exception as detail : # Catch ALL exceptions
		message = "Uniflow Error - Unable to retrieve run dictionary when parsing JSON " + JSON + '\n' + traceback.format_exc()
		LogAndEmail( message , 4 )
		return None	
	
''' Sets the state of an run.  If run 
    does not exist it will be created.
'''
def SetUNIFlowState( flowcellID , state ) :
	
	LogAndEmail( "Setting " + flowcellID + " to " + state , 0 )
	
	values = { 
	'userId'     : globalOptions['TROVAEMON_ID'], 
	'password'   : globalOptions['TROVAEMON_PWD'], 
	'stepName'   : 'Update Run Status', 
	'Submit'     : 'true', 
	'flowcellID' : flowcellID , 
	'status'     : state 
	}
	
	url_encoded_values = urllib.urlencode( values )
	request            = urllib2.Request( globalOptions['UNIFLOW_URL'] , url_encoded_values )
	response           = urllib2.urlopen( request )
	code               = response.getcode()
	
	if code != 200 :
		message = "ERROR: TrovapipeUtils~UNIFlow Error - response code was not 200 (not okay) when setting state of run: " + \
		runID + " to " + state + " response: " + str( response.getcode() )
		LogAndEmail( message , 3 )
		sys.exit()
		
	return code
	
''' Determines if this instance is a clone
    if so kills the process
'''
def NoClone( LOCK_FILE ) :
	pid     = str( os.getpid() )
	pidfile = LOCK_FILE
		
	if os.path.isfile( pidfile ) :
		if IsDead( pidfile ) :
			 file( pidfile , 'w' ).write( pid )
			 logging.warning( "A lock.pid file existed with a dead process..." )
		else :
			logging.info( "Terminating analysis, a process already exists..." )
			sys.exit()
	else:
		file( pidfile , 'w' ).write( pid )	
		
''' Process ID file still exists suggesting this
    code is already running.  Verify that's true.		
'''
def IsDead( pid_file ) :
	with open( pid_file , 'rb' ) as input :
		pid = input.readline().strip()
		if psutil.pid_exists( int( pid ) ) : return False
		else : return True
	
''' Archives logs when they get too large
'''
def ArchiveLog( APP_LOG ) :
	
	if not os.path.exists( APP_LOG ) : open( APP_LOG , 'w' ).close()
		
	if os.path.getsize( APP_LOG ) > globalOptions['MAX_LOG_SIZE'] : 
	
		base = os.path.basename( APP_LOG ).split('.')[0]
		archive_dir = os.path.join(  os.path.dirname( APP_LOG ) , 'archive' )
		
		indices = [ 0 ]
		files = glob.glob( os.path.join( archive_dir , base + "*" ) )
		for file in files :
			indices.append( int( file.split('.')[ 1 ] ) )
			
		new_index = max( indices ) + 1
		new_archive_file = os.path.join( archive_dir , base + '.' + str( new_index ) + '.log' )
		if os.path.exists( APP_LOG ) : shutil.move( APP_LOG , new_archive_file )
