#!/usr/bin/env python
import os
import sys
import time
import datetime
import subprocess
import atexit
import logging
import traceback
import requests
from Keys import Keys as limskeys
from Utilities import TrovapipeUtils as tputils
import glob
import inspect
from configobj import ConfigObj
import shlex
import shutil

# date: 4/13/16
# name: Thomas Richardson
# email: trichardson@trovagene.com
#
# description: Starts from cron and monitors a MiSeq run respository looking
#              for analyzed runs ready for upload to Trovabase. Archives results.
#
#              1. Finds analyzed run data
#              2. Uploads it to Trovabase
#              3. Moves the run folder (and runFolder/Trovapipe_Results within) to an archive subdir
#
#              Has other features such as ability to prevent a clone of the process
#              etc..

#
# MODIFICATIONS : 11/3/2016 by Palak Sheth

CONFIG_FILE         = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'TrovaWrapper_config.ini' )

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

APP_NAME         = 'CLIA Run Archive Daemon'
LOCK_FILE        = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'archivedaemon.lock.pid' )                    # Prevent multiple processes
APP_LOG          = os.path.join( os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'Log' ) , 'archivedaemon.log' ) # App log
MAX_LOG_SIZE     = globalOptions['MAX_LOG_SIZE']

VERSION = globalOptions['VERSION']

''' Serial steps to upload and archive one run
'''
def Process() :

	# get list of repos
	repositories = tputils.Repositories()
	
	# process list of repos and get dictionary of analyzeable runs
	runDirs = CheckRuns( repositories )
	
	# process dictionary of runs
	if runDirs != None :
		for flowcellID, runDirDict in runDirs.iteritems():
			full_root_run_path = os.path.realpath( runDirDict['run_dir'] )
			ArchiveRun( full_root_run_path , runDirDict['repo_path'] , runDirDict['flowcellID'], runDirDict['run_folder'] )



''' Iterate uniflow NGS runs where status indicates they
    are ready for upload to trovabase & return only one ( or None )
'''
def CheckRuns( repositories ) :
	
	runDirs = {}
	
	statuses = [ limskeys.NGS_TROVABASE_UPLOAD_ERROR, limskeys.NGS_ANALYSIS_COMPLETE ]

	for status in statuses:
	
		results = tputils.QueryRunsByStatus( status )

		for flowcellID , metadata in results.iteritems() :
			if flowcellID != 'null' :
				for repo_path in repositories :
					run_dir = glob.glob( os.path.join( repo_path , '*' + flowcellID ) )
					if len( run_dir ) > 1 :     # Zero is okay, > 1 is NOT okay, 
						message = "ERROR: More than one run exists in the repository with the same " \
						   + "flowcellID. This is an error condition which must be fixed.\n"
						for dir in run_dir :
							message += dir + '\n'
						tputils.LogAndEmail( message , 2 )
						tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
					elif len( run_dir ) == 1 :
						run_folder = os.path.basename(os.path.normpath( run_dir[ 0 ] ))
						runDirs[ flowcellID ] =  { \
												'run_dir' : run_dir[ 0 ], \
												'flowcellID' : flowcellID, \
												'repo_path' : repo_path, \
												'run_folder' : run_folder \
												}
						#return run_dir[ 0 ] , flowcellID , repo_path, run_folder
					else : continue # Run was not in this repository
	
	if len(runDirs) > 0:
		return runDirs
	else:			
		return None

''' 
    Archive the run
'''
def ArchiveRun( run_root , repo_path , flowcellID, run_folder_name ):
	
	tputils.LogAndEmail( "Starting archive for run: " + run_root + ' to ' + repo_path + '/archive/', 0 )
	
	# check if archive folder exists
	archive_folder = os.path.join( repo_path, 'archive')
	if not archive_folder.endswith('/'):
		archive_folder = archive_folder + '/'
	if not os.path.exists( archive_folder ):
		os.makedirs( archive_folder )
	
	# rsync run folder into archive folder
	CMD = "rsync -azu " + run_root.rstrip(str(os.sep)) + " " + archive_folder
	print "Running command: " + CMD
	p1 = subprocess.Popen( shlex.split(CMD) , stdout=subprocess.PIPE , stderr=subprocess.STDOUT )
		
	stdout , stderr = p1.communicate()
		
	if 'rsync' in stdout or 'failed' in stdout or stderr != None:
		message = "ERROR: A error occurred when using rsync to archive " + run_root + ' to ' + archive_folder + ' ' + stdout 
		if stderr != None :
			message += ( ' ' + stderr )
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ARCHIVE_ERROR )
		tputils.LogAndEmail( message , 4 )
		sys.exit(1)
	else:
		print "Rsync complete from: " + run_root + " to: " + archive_folder
		
	# check hashes to make sure archive folder equals run folder, then only remove
	runId = os.path.basename( run_root.rstrip(str(os.sep)) )
	runFolderHash = GetHashofDirs( run_root )
	archiveFolderHash = GetHashofDirs( os.path.join( archive_folder, runId ) )
	doRemove = False
	if not runFolderHash == archiveFolderHash:
		print "RUN FOLDER HASH: " + runFolderHash
		print "ARCHIVE FOLDER HASH: " + archiveFolderHash
		msg = "ERROR: run folder checksum and archive folder checksum do not match! Something went wrong with the archiving process for run folder " + run_root + " to " + archive_folder
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ARCHIVE_ERROR )
		tputils.LogAndEmail( msg , 4 )
		sys.exit(1)	
	else:
		print "Original run folder and archive folder hashes match! Continuing with archive..."
		## create symlink to archived dir in generic run repo
		#GENERIC_RUN_REPO = globalOptions['GENERIC_RUN_REPO']
		#if not os.path.exists( GENERIC_RUN_REPO ):
			#os.makedirs( GENERIC_RUN_REPO )
		#symlinkPath = os.path.join( GENERIC_RUN_REPO, runId )
		#if not os.path.exists( symlinkPath ):
			#os.symlink( os.path.join( archive_folder, runId ).rstrip(str(os.sep)), symlinkPath )
		doRemove = True
	
	# After archiving delete the leftover directories from the main repo dir
	if doRemove == True:
		CMD = 'rm -rf ' + run_root
		print "Running command: " + CMD
		p2 = subprocess.Popen( shlex.split(CMD) , stdout=subprocess.PIPE , stderr=subprocess.STDOUT )
		
		stdout , stderr  = p2.communicate()

		if len( stdout ) != 0 or stderr != None:
			message = "ERROR: An error occurred while trying to delete the run folder from the repository after an archived copy was made: " + run_root + ' ' + stdout 
			if stderr != None :
				message += ( ' ' + stderr )
			tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ARCHIVE_ERROR )
			tputils.LogAndEmail( message , 4 )
			sys.exit(1)	
		
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ARCHIVE_COMPLETE )
		
		tputils.logging.info( "Finished archive for run: " + run_root + ' moved to ' + archive_folder )
		
		

''' Upload results to trovabase
	Results are in a runfolder/Trovabase_Results directory
    Archive the run and results
'''
def UploadToTrovabase( run_root , repo_path , flowcellID, run_folder_name ) :

	run_path = os.path.join( repo_path , run_root )
	
	tputils.LogAndEmail( "Starting Trovabase upload and archive for run: " + run_path , 0 )
	
	results_cache = os.path.join( run_path , limskeys.TROVAPIPE_RESULTS_DIR, run_folder_name )
	
	sample_sheet_path         = ''
	run_qc_report_path        = ''
	summary_results_path      = ''
	statistics_results_path   = ''

	sample_sheet_pattern       = '_sheet'
	run_qc_report_pattern      = 'RunQuality'
	summary_results_pattern    = '_summary'
	statistics_results_pattern = '_stats'

	
	csv_files = glob.glob( os.path.join( results_cache , '*.csv' ) )
	
	# Verify only the exact 4 file names
	# are in the results cache.
	# Collect their paths.
	duplicate_files = False
	
	for file in csv_files :
		if sample_sheet_pattern in file :
			if sample_sheet_path == '' :
				sample_sheet_path = os.path.join( results_cache , file )
			else : duplicate_files = True
		if run_qc_report_pattern in file :
			if run_qc_report_path == '' :
				run_qc_report_path = os.path.join( results_cache , file )
			else : duplicate_files = True
		if summary_results_pattern in file :
			if summary_results_path == '' :
				summary_results_path = os.path.join( results_cache , file )
			else : duplicate_files = True
		if statistics_results_pattern in file :
			if statistics_results_path == '' :
				statistics_results_path = os.path.join( results_cache , file )
			else : duplicate_files = True
	
	if duplicate_files :
		message = "~Trovabase Error - The results cache has more than one file for a " + \
			"result type making it impossible to select the proper results to upload to Trovabase: " + results_cache
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_TROVABASE_UPLOAD_ERROR )
		tputils.LogAndEmail( message , 4 )
		sys.exit()
		
	if not os.path.exists( sample_sheet_path ) or \
		not os.path.exists( run_qc_report_path ) or \
		not os.path.exists( summary_results_path ) or \
		not os.path.exists( statistics_results_path ) :
			message = "An upload file is missing from the cache: "  + results_cache 
			message += " Please fix the problem before trying to upload to Trovabase."
			tputils.SetUNIFlowState( flowcellID , limskeys.NGS_TROVABASE_UPLOAD_ERROR )
			tputils.LogAndEmail( message , 4 )
			sys.exit()
			
	retcode = subprocess.call( [ 'java' , '-jar' , TROVABASE_JAR , '-database' , DATABASE , '-group' , 'CLIA' , \
		'-s' , sample_sheet_path , \
		'-r' , summary_results_path ,\
		'-stat' , statistics_results_path ,\
		'-q' , run_qc_report_path ] , \
		stdout=None , stderr=subprocess.STDOUT )

	if retcode != 0 :
		message = "A non-zero exit code was returned when using " + TROVABASE_JAR + " to upload " + results_cache + ". Code: " + str( retcode )
		tputils.LogAndEmail( message , 4 )
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_TROVABASE_UPLOAD_ERROR )
		sys.exit()
		
	logging.info( "Finished Trovabase upload for run: " + run_path )
	logging.info( "Using rsync to move the run to the archive." )
	
	archive = os.path.join( repo_path , 'archive' )
		
	# rsync the results deleting the files, leaving the directories
	p1 = subprocess.Popen( [ 'rsync' , '-a' , '--remove-source-files' , run_path , archive ] , \
		stdout=subprocess.PIPE , stderr=subprocess.STDOUT )
		
	stdout , stderr = p1.communicate()
		
	if 'rsync' in stdout or 'failed' in stdout or stderr != None:
		message = "A error occurred when using rsync to archive " + run_path + ' ' + stdout 
		if stderr != None :
			message += ( ' ' + stderr )
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ARCHIVE_ERROR )
		tputils.LogAndEmail( message , 4 )
		sys.exit()
	
	# After archiving delete the leftover directories from the main repo dir
	p2 = subprocess.Popen( [ 'find' , run_path , '-depth' , '-type' , 'd' , '-empty' , '-exec' , 'rmdir' , '{}' , ';' ] , \
		stdout=subprocess.PIPE , stderr=subprocess.STDOUT )
	
	stdout , stderr  = p2.communicate()

	if len( stdout ) != 0 or stderr != None:
		message = "An error occurred while trying to delete the run folder from the repository after an archived copy was made: " + run_path + ' ' + stdout 
		if stderr != None :
			message += ( ' ' + stderr )
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ARCHIVE_ERROR )
		tputils.LogAndEmail( message , 4 )
		sys.exit()	
		
	tputils.SetUNIFlowState( flowcellID , limskeys.NGS_UPLOADED_TO_TROVABASE )
		
	tputils.logging.info( "Finished archive for run: " + run_path + ' moved to ' + archive )
	

def GetHashofDirs(directory, verbose=0):
	import hashlib, os
	SHAhash = hashlib.sha1()
	if not os.path.exists (directory):
		return -1
    
	try:
		for root, dirs, files in os.walk(directory):
			for names in files:
				if verbose == 1:
					print 'Hashing', names
				filepath = os.path.join(root,names)
				try:
					f1 = open(filepath, 'rb')
				except:
					# You can't open the file for some reason
					f1.close()
					continue

				while 1:
					# Read file in as little chunks
					buf = f1.read(4096)
					if not buf : break
					SHAhash.update(hashlib.sha1(buf).hexdigest())
				f1.close()

	except:
		import traceback
		# Print the stack traceback
		traceback.print_exc()
		return -2

	return SHAhash.hexdigest()
	
''''''''''''''''''''''''
''' Main	
'''''''''''''''''''''
if __name__=="__main__" :
 
	try :
	
		tputils.ArchiveLog( APP_LOG )		
		logging.basicConfig( filename=APP_LOG , level=logging.DEBUG )
		logging.info( 'Starting ' + APP_NAME + ' ' + datetime.datetime.fromtimestamp( time.time() ).strftime( '%Y-%m-%d %H:%M:%S' ) ) 
	
		tputils.NoClone( LOCK_FILE )                              # Kill process and don't remove lock if it's a clone
		atexit.register( tputils.CleanUp , LOCK_FILE , APP_NAME ) # Kill the lock at exit

		Process()
		
	except Exception as detail : # Catch ALL exceptions
		tputils.LogAndEmail( APP_NAME + " crashed: " + str( detail ) + ' ' + traceback.format_exc() , 4 )
