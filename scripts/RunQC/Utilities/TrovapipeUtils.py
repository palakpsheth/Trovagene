#!/usr/bin/env python
import logging
import os
import psutil
import time
import datetime
import urllib
import urllib2
from email.mime.text import MIMEText
from Keys import Keys as limskeys
import smtplib
import traceback
import subprocess
import sys
import glob
import shutil
import xml.etree.ElementTree as ET

# UNIVERSAL
SILENCE_EMAIL = False
TROVAEMON_ID  = "trovaemon"
TROVAEMON_PWD = "trovaemon123"
TROVABASE_JAR    = '/mnt/data/Bioinformatics/trovapipe/trovabase/v13/upload.jar'
TROVAPIPE_SCRIPT_LOCATION  = '/home/palak/isilon/BI-125-trovapipe-structure-modification/DataAnalysisWrapper_1604v1_0_0.py'
MAX_LOG_SIZE  = 500000000   # (500 Mb) 

# TESTING
DATABASE         = 'trovabase_dev' # test
UNIFLOW_URL   = 'https://trovagene_dev.uniconnect.com:8100/uniflow' # test
REVIEW_CACHE  = '/mnt/rnd/Bioinformatics/trovapipe_DEV/review' # test

# PRODUCTION
#UNIFLOW_URL   = 'https://trovagene.uniconnect.com/uniflow' # production
#DATABASE         = 'trovabase' # production
#REVIEW_CACHE  = '/mnt/prd/review/' # production

''' Returns a list of paths to MiSeq repositories
'''
def Repositories() :
	
	repositories_file = os.path.join( "Utilities" , "repositories.xml" )
	#msg = "Repo file used " + repositories_file
	#logging.info( msg )
	#msg = "Repo file used " + os.path.abspath( repositories_file )
	#logging.info( msg )
	
	if not os.path.exists( repositories_file ) :
		logging.critical( "The Utilities/repositories.xml file is missing.  Analysis cannot proceed..." )
		logging.critical( os.getcwd() )
		sys.exit()

	tree = ET.parse( repositories_file )
	root = tree.getroot()
	
	repositories = list()
	
	for child in root:
		if child.tag == "repository" :
			repositories.append( child.text )
			#msg = "Repo identified " + child.text
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
def LogAndEmail( message , priority ) :

	if priority == 0 :
		logging.info( message )
	elif priority > 0 :
		logging.error( message )
		Email( message , priority )
		
''' Email message to bioinfo
'''
def Email( message , priority ) :

	if SILENCE_EMAIL : return
	
	msg = MIMEText( message )

	distribution_list = os.path.join( "Utilities" , "email.xml" )
	
	priority_1 = list() # not currently used, mostly for warnings
	priority_2 = list() # basic error
	priority_3 = list() # moderate error, not used
	priority_4 = list() # critical error
	
	if not os.path.exists( distribution_list ) :
		logging.critical( "Email distribution list is not accessible.  The message below was not delivered: " )
		logging.critical( message )
		sys.exit()
		
	tree = ET.parse( distribution_list )
	root = tree.getroot()
		
	for child in root:
		if child.tag == "Priority-1" :
			for grandchild in child :
				if grandchild.tag == "address" :
					priority_1.append( grandchild.text )
		elif child.tag == "Priority-2" :
			for grandchild in child :
				if grandchild.tag == "address" :
					priority_2.append( grandchild.text )
		elif child.tag == "Priority-3" :
			for grandchild in child :
				if grandchild.tag == "address" :
					priority_3.append( grandchild.text )
		elif child.tag == "Priority-4" :
			for grandchild in child :
				if grandchild.tag == "address" :
					priority_4.append( grandchild.text )
	
	send_list = ""
	
	if priority == 1 :
		send_list = ",".join( priority_1 )
	elif priority == 2 :
		send_list = ",".join( priority_2 )
	elif priority == 3 :
		send_list = ",".join( priority_3 )
	elif priority == 4 :
		send_list = ",".join( priority_4 )
		
	me  = "trovaemon@trovagene.com"

	# use this later to automatically generate tickets?
	#cc  = "support@trovagene.atlassian.net"
	
	me  = "trovaemon@trovagene.com"
	msg['Subject'] = 'AUTOMATED TROVAPIPE MESSAGE: Error'
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
def UploadRunResultsToUniflow( results_cache , flowcellID , run_folder_name ) :

	try :
	
		# Verify all results files exist 
		
		wide_results  = "" # Homo sapiens readable
		raw_results   = ""
		sample_sheet  = ""
		stats_results = ""
		db_results    = "" # database readable
		runqc_results = ""
		log_file      = ""
		
		outfiles_dir = os.path.join( results_cache, run_folder_name )
		review_cache = os.path.join( REVIEW_CACHE , run_folder_name )
		if os.path.exists( review_cache ) : shutil.rmtree( review_cache )
		os.mkdir( review_cache )
		
		#results_files = glob.glob( os.path.join( results_cache , '*.csv' ) )
		#log_files = glob.glob( os.path.join( results_cache , '*.txt' ) )
		
		qc_files = glob.glob( os.path.join( results_cache , '*.csv' ) )
		for file in qc_files :
			if 'RunQuality' in file :
				runqc_results = file
				#shutil.copy( os.path.join( results_cache , file ) , review_cache )
				shutil.move( os.path.join( results_cache , file ) , outfiles_dir )
		
		results_files = glob.glob( os.path.join( outfiles_dir , '*.csv' ) )
		for file in results_files :
			if file.endswith( '_raw.csv' ) :
				raw_results = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
			elif file.endswith( '_sheet.csv' ) :
				sample_sheet = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
			elif file.endswith( '_stats.csv' ) :
				stats_results = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
			elif file.endswith( '_summary.csv' ) :
				db_results = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
			elif file.endswith( '_wide.csv' ) :
				wide_results = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
			elif 'RunQuality' in file :
				runqc_results = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
		
		log_files = glob.glob( os.path.join( outfiles_dir , '*.txt' ) )
		for file in log_files :
			#if file.startswith( 'log' ) :
			if file.endswith( '.txt' ) :
				log_file = file
				shutil.copy( os.path.join( outfiles_dir , file ) , review_cache )
				
		#wide_results = db_results.replace( '_summary', '' ) # wide results has no '_' extension
		#wide_results = db_results.replace( '_summary', '_wide' ) # wide results has no '_' extension
		
		#if not os.path.exists( wide_results ) or raw_results == "" or sample_sheet == "" or stats_results == "" or db_results == "" or runqc_results == "" or log_file == "" :
		if wide_results == "" or raw_results == "" or sample_sheet == "" or stats_results == "" or db_results == "" or runqc_results == "" or log_file == "" :
			LogAndEmail( 'Trovapipe Results missing from results cache: ' + outfiles_dir + '\nwide_results: ' + wide_results + '\nraw_results: ' + raw_results + '\nsample_sheet: ' + sample_sheet + '\nstats_results: ' + stats_results + '\ndb_results: ' + db_results + '\nrunqc_results: ' + runqc_results + '\nlog_file: ' + log_file, 3 )
			sys.exit()
		#else : 
		#	shutil.copy( os.path.join( results_cache , wide_results ) , review_cache )
	
		LogAndEmail( 'Uploading trovapipe results to uniflow: ' + outfiles_dir , 0 )
	
		batchID = 'RB' + flowcellID
		
		proc = subprocess.Popen( [ 'curl' , \
			'-F' , 'userId=' + TROVAEMON_ID , \
			'-F' , 'password=' + TROVAEMON_PWD , \
			'-F' , 'stepName=API Result Upload' , \
			'-F' , 'batchId=' + batchID , \
			'-F' , 'flowCellID=' + flowcellID , \
			'-F' , 'status=success' , \
			'-F' , 'formNumber=0' , \
			'-F' , 'Submit=true' , \
			'-F' , 'accountId=Trovagene' , \
		    '-F' , 'csvResultsFile=@' + db_results , \
			UNIFLOW_URL ] ,  stdout=subprocess.PIPE , stderr=subprocess.PIPE )
				  
		out, err = proc.communicate()
		both     = out + err

		if "SYSTEM EXCEPTION" in both or "<span>*1" in both or "couldn't open file" in both :
			message = "An error occurred while trying to upload a csv results file to UniFlow using curl: " + db_results + '\n' + both
			LogAndEmail( message , 4 )
			sys.exit()	
			
	except Exception as detail : # Catch ALL exceptions 
		message = "An error occurred while trying to upload a csv results file to UniFlow using curl: " + db_results + '\n' + traceback.format_exc()
		LogAndEmail( message  , 4 )
	
''' Gets the state of the run from UNIFlow
    by way of a RESTful API
	- if parsing error return None
	- if exists return state, if not create and set/return
'''	
def GetUNIFlowState( flowcellID ) :
 
	values = { 
	'userId'     : TROVAEMON_ID, 
	'password'   : TROVAEMON_PWD, 
	'stepName'   : 'Query Run Status', 
	'Submit'     : 'true', 
	'flowcellID' : flowcellID 
	}
	
	data     = urllib.urlencode( values )
	request  = urllib2.Request( UNIFLOW_URL , data )
	response = urllib2.urlopen( request )

	JSON     = response.read()
		
	results = dict()
	
	try :
		results = ParseJSONOneRun( JSON )
	except Exception as detail : # Catch ALL exceptions
		message = "UNIFlow Error - Unable to parse JSON when querying state of flowcellID: " + flowcellID + " " + str( detail ) + " " + traceback.format_exc()
		LogAndEmail( message , 3 )
		return None
		
	if 'status' not in results or 'flowcellID' not in results :
		message = "UNIFlow Error - Unable to find status or flowcellID results when querying state of run: " + flowcellID
		LogAndEmail( message , 3 )
		return None
	
	else :
	
		if results[ 'status' ] == 'NONE' and results[ 'flowcellID' ] == 'NGS_RUN_DOES_NOT_EXIST' :
			response_code = SetUNIFlowState( flowcellID , limskeys.NGS_RUN_PENDING )
			if response_code == 200 : return limskeys.NGS_RUN_PENDING
			else :
				message = "UNIFlow Error - response code was not 200 (not okay) when setting state of run: " + \
				flowcellID + " to " + limskeys.NGS_RUN_PENDING
				LogAndEmail( message , 3 )				
				return None
		else :
			return results[ 'status' ]
	
''' Returns flowcellID and metadata for runs
    with the specified status
'''
def QueryRunsByStatus( status ) :
	
	values = {
	'userId'  : TROVAEMON_ID,
	'password': TROVAEMON_PWD,
	'stepName': 'Query Runs By Status',
	'Submit'  : 'true', 
	'status'  : status
	}
	
	url_encoded_values = urllib.urlencode( values )
	request            = urllib2.Request( UNIFLOW_URL , url_encoded_values )
	response           = urllib2.urlopen( request )
	JSON               = response.read()
	
	if "SYSTEM EXCEPTION" in JSON :
		message = "Uniflow Error - Error when attempting to query UNIFlow stepName: Query Runs By Status.\nUNIFlow output: " + JSON
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
	'userId'     : TROVAEMON_ID, 
	'password'   : TROVAEMON_PWD, 
	'stepName'   : 'Update Run Status', 
	'Submit'     : 'true', 
	'flowcellID' : flowcellID , 
	'status'     : state 
	}
	
	url_encoded_values = urllib.urlencode( values )
	request            = urllib2.Request( UNIFLOW_URL , url_encoded_values )
	response           = urllib2.urlopen( request )
	code               = response.getcode()
	
	if code != 200 :
		message = "TrovapipeUtils~UNIFlow Error - response code was not 200 (not okay) when setting state of run: " + \
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
		
	if os.path.getsize( APP_LOG ) > MAX_LOG_SIZE : 
	
		base = os.path.basename( APP_LOG ).split('.')[0]
		archive_dir = os.path.join(  os.path.dirname( APP_LOG ) , 'archive' )
		
		indices = [ 0 ]
		files = glob.glob( os.path.join( archive_dir , base + "*" ) )
		for file in files :
			indices.append( int( file.split('.')[ 1 ] ) )
			
		new_index = max( indices ) + 1
		new_archive_file = os.path.join( archive_dir , base + '.' + str( new_index ) + '.log' )
		if os.path.exists( APP_LOG ) : shutil.move( APP_LOG , new_archive_file )
