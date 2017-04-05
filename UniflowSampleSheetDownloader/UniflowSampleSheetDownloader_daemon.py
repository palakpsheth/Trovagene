#!/usr/bin/python
import os
import sys
import time
import datetime
import subprocess
import psutil
import atexit
import logging
import traceback
import requests
sys.path.append( os.path.dirname( os.path.dirname(os.path.realpath(__file__) ) ) )
sys.path.append( os.path.join( os.path.dirname( os.path.dirname(os.path.realpath(__file__) ) ), 'bin' ) )
from TrovaWrapper.Keys import Keys as limskeys
import glob
import shutil
from TrovaWrapper.Utilities import TrovapipeUtils as tputils
import inspect
from configobj import ConfigObj
from scripts.sampleSheetValidator import SampleSheetValidator as ssv
import urllib2
import urllib
import hashlib
import filecmp
import StringIO
# import error code modules
import DataAnalysisWrapperErrors as dawe


CONFIG_FILE = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'config.ini' )

# load config file
if not os.path.exists( CONFIG_FILE ) :
	msg = str('ERROR: The UniflowSampleSheetDownloader config.ini file "' + CONFIG_FILE + '" is missing.  Download cannot proceed...')
	tputils.LogAndEmail( msg, 4)
	sys.exit(1)
Config = ConfigObj(CONFIG_FILE, raise_errors=True)
# load global section
globalOptions = Config['global']

APP_NAME         = 'Uniflow Sample Sheet Downloader Daemon'
LOCK_FILE        = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'uniflowsamplesheetdownloaderdaemon.lock.pid' )                    # Prevent multiple processes
APP_LOG          = os.path.join( os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'Log' ) , 'uniflowsamplesheetdownloaderdaemon.log' ) # App log
if not os.path.exists( os.path.dirname( APP_LOG )):
	os.makedirs( os.path.dirname( APP_LOG ))

VERSION = globalOptions['VERSION']

def getUrlResultHash(fname):
	hash_md5 = hashlib.md5()
	#with open(fname, "rb") as f:
	for chunk in iter(lambda: fname.read(4096), b""):
		hash_md5.update(chunk)
	return hash_md5.hexdigest()

def getFileHash(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
		return hash_md5.hexdigest()

''' Serial steps to analyze one run
'''
def Process() :

	# get list of repos
	repositories = tputils.SSRepositories( Config )
	
	# process list of repos and get dictionary of downloadable sampleSheets
	sampleSheets = CheckRuns( )
	
	# process dictionary of sampleSheets
	if sampleSheets != None :
		DownloadAndValidate( sampleSheets )
		
	# archive used and old samplesheets
	Archive( repositories, globalOptions['MAX_AGE_DAYS'] )


def CheckRuns( ) :

	results = tputils.QueryRunsByStatus( limskeys.NGS_RUN_PENDING, globalOptions['UNIFLOW_URL']  )
	
	sampleSheets = {}
	

	print 'FOUND ' + str(len(results)) + ' flowcellIDs with status ' + limskeys.NGS_RUN_PENDING
	for flowcellID , metadata in results.iteritems() :
		if flowcellID != 'null' :
			print '\tflowcellID: ' + flowcellID
			#print 'metadata: ' + str(metadata)
			# try to fetch sampleSheet csv for this flowcell
			# https://trovagene_dev.uniconnect.com:8100/sampleWorksheets/MS0000000-AU5LH.csv
			# https://trovagene_dev.uniconnect.com:8100/sampleWorksheets/MS0000000-AU5LH.csv
			#urlId = 'MS' + flowcellID[3:]
			urlId = flowcellID + '_SampleSheet.csv'
			#url = 'https://trovagene_dev.uniconnect.com:8100/sampleWorksheets/' + urlId
			#https://trovagene_dev.uniconnect.com:8100/sampleWorksheets/000000000-KRASOLD_SampleSheet.csv
			if not globalOptions['UNIFLOW_SS_URL'].endswith('/'):
				globalOptions['UNIFLOW_SS_URL'] = globalOptions['UNIFLOW_SS_URL'] + '/'
			url = globalOptions['UNIFLOW_SS_URL'] + urlId
			print "\tTRYING URL: " + url
			try:
				csv = urllib2.urlopen(url)
				print 'URL: ' + url
				print '\tHTTP STATUS RETCODE: ' + str(csv.getcode())
				if csv.getcode() == 200:
					sampleSheets[ flowcellID ] = url
			except Exception as detail : # Catch ALL exceptions
				#tputils.LogAndEmail( 'WARNING: No SampleSheet found for flowcellID: ' + str(flowcellID), 0 )
				#print '\t\tEXCEPTION: ' + traceback.format_exc()
				print "\tSAMPLESHEET NOT FOUND!"
				continue
	print 'Found ' + str(len(sampleSheets)) + ' sampleSheets for download'
	print
	if len(sampleSheets) > 0:
		tputils.LogAndEmail( 'Found ' + str(len(sampleSheets)) + ' SampleSheet(s) for download', 0)
		return sampleSheets
	else:
		return None


def DownloadAndValidate( sampleSheets ) :
	# get sampleSheet repos
	reposDict = tputils.SSRepositoriesDict( Config )
	
	validated = 0
	downloaded = 0
	for flowcellID, url in sampleSheets.iteritems():
		
		# fetch the sample sheet
		samplesheet = urllib2.urlopen(url)
		ssFileHash = getUrlResultHash( samplesheet )
		
		# get the instrument this samplesheet belong to
		miseqID = getInstrumentID( samplesheet )
		if miseqID == None:
			miseqID = 'all'
		
		print 'FlowcellID: ' + flowcellID
		print 'URL: ' + url
		print 'MiSeqID: ' + miseqID
		
		# get the correct repo path
		for key, value in reposDict.iteritems():
			if str(miseqID) == str(key):
				repoPath = value
				break
		
		print 'repoPath: ' + repoPath
		
		# define name of ss
		ssName = os.path.join( repoPath, flowcellID + '_SampleSheet.csv' )
		invalidName = os.path.join( repoPath, flowcellID + '_SampleSheet.csv.invalid' )
		
		doDownload = 1;
		# if file already file exists check its hash
		if os.path.isfile( ssName ):
			existingHash = getFileHash( ssName )
			if (ssFileHash == existingHash):
				doDownload = 0
		elif os.path.isfile( invalidName ):
			existingHash = getFileHash( invalidName )
			if (ssFileHash == existingHash):
				doDownload = 0
		#print "OLD HASH: " + str(existingHash) + " NEW HASH: " + str(ssFileHash)
		
		
		if doDownload == 1:
			# run ss validator if option=True
			if globalOptions['runSSV'].upper() == 'TRUE' or globalOptions['runSSV'] == True:
				#def runSSV_ssOnly( sample_sheet, ss_outfile, ss_infer_info ):
				#ssv.runSSV( samplesheet, ssName, globalOptions['ss_infer_info'] )
				try:
					# clean up old files
					if os.path.isfile( ssName ): os.remove( ssName )
					if os.path.isfile( invalidName ): os.remove( invalidName )
					# run SSV
					ssv.runSSV( url, ssName, globalOptions['ss_infer_info'] )
					validated = validated + 1
					downloaded = downloaded + 1
					print
					print 'Validated SampleSheet: ' + ssName
					print
				except (dawe.UnknownOSError, dawe.OptionError, dawe.PathError, dawe.SSValidatorError, dawe.PipelineError, dawe.ConfigFileError, dawe.SequencingQcError, dawe.ReadsProcessingError) as err:
					msg = "WARNING %d: %s" % (err.args[0], err.em[err.args[0]])
					tputils.LogAndEmail( APP_NAME + " message for flowcellID " + flowcellID + " : " + msg, 4, Config["emails"] )
					urllib.urlretrieve (url, invalidName)
					downloaded = downloaded + 1
					print
					print 'Unvalidated SampleSheet: ' + ssName
					print
					continue;
				except:
					raise
				
			#else:
			#	urllib.urlretrieve (url, ssName)
			
		else:
			print 'Skipping sampleSheet download because it alreadys exists: ' + invalidName
		print
	tputils.LogAndEmail('Validated: ' + str(validated) + ' SampleSheet(s) and Downloaded: ' + str(downloaded) + ' SampleSheet(s)', 0)

def Archive( repos, MAX_AGE_DAYS ):
	
	statuses = [ limskeys.NGS_CLIA_REVIEW, limskeys.NGS_TROVABASE_UPLOAD_ERROR, limskeys.NGS_ARCHIVE_COMPLETE, limskeys.NGS_ANALYSIS_COMPLETE ]
	
	archiveCount = 0
	
	for status in statuses:
	
		results = tputils.QueryRunsByStatus( status )
		
		for repo in repos:
			files_in_repo = glob.glob( os.path.join( repo, '*_SampleSheet.csv' ) )
			for samplesheet in files_in_repo:
				archive=False
				ssflowcellID = os.path.basename(samplesheet).split('_SampleSheet.csv')[0]
				
				# first check if the flowcellID has been used
				for flowcellID , metadata in results.iteritems() :
					if str(flowcellID) == str(ssflowcellID) : archive=True
				
				# then 	check if the sampleSheet is too old
				if archive == False:
					if (time.time() - os.path.getmtime(samplesheet) > (MAX_AGE_DAYS * 24 * 60 * 60)):
						archive = True
						
				# then archive it
				if archive == True:
					if not os.path.exists( os.path.join(repo,'archive') ):
						os.makedirs( os.path.join(repo,'archive') )
					shutil.move(samplesheet, os.path.join(repo,'archive',os.path.basename(samplesheet)))
					archiveCount = archiveCount + 1
					tputils.LogAndEmail("SampleSheet " + samplesheet + " archived to " + os.path.join(repo,'archive'), 0)
					print "SampleSheet " + samplesheet + " archived to " + os.path.join(repo,'archive')
	
	print
	tputils.LogAndEmail('Archived ' + str(archiveCount) + ' SampleSheet(s)', 0)


def getInstrumentID( samplesheet ):
	
	return None
	
	
	
''''''''''''''''''''''''
''' Main	
'''''''''''''''''''''
if __name__=="__main__" :

	try :
	
		tputils.ArchiveLog( APP_LOG )			
		logging.basicConfig( filename=APP_LOG , level=logging.DEBUG )
		logging.info( 'Starting ' + APP_NAME + ' ' + \
					  datetime.datetime.fromtimestamp( time.time() ).strftime( '%Y-%m-%d %H:%M:%S' ) )  

		tputils.NoClone( LOCK_FILE )                              # Kill process and don't remove lock if it's a clone
		atexit.register( tputils.CleanUp , LOCK_FILE , APP_NAME ) # Kill the lock at exit
		
		Process()
	
	except Exception as detail : # Catch ALL exceptions
		tputils.LogAndEmail( APP_NAME + " crashed: " + str( detail ) + ' ' + traceback.format_exc() , 4 )
