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
from Keys import Keys as limskeys
import glob
import shutil
from Utilities import TrovapipeUtils as tputils
import inspect
from configobj import ConfigObj


# Date: 3/04/16
# Revision: 6/13/16
# Name: Thomas Richardson
# Email: trichardson@trovagene.com
#
# Description: Starts from cron and monitors a MiSeq run respository looking
#              for completed runs waiting for analysis.
#
#              1. Analyzes the run data
#              2. Uploads the results to UNIFlow
#              3. Stores the results within the run for later upload into Trovabase
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

APP_NAME         = 'CLIA Trovapipe Analysis Daemon'
FASTQ_DIR_SUFFIX = os.path.join( os.path.join( "Data" , "Intensities" ) , "BaseCalls" )                                         # Data/Intensities/Basecalls
LOCK_FILE        = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'analysisdaemon.lock.pid' )                    # Prevent multiple processes
APP_LOG          = os.path.join( os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'Log' ) , 'analysisdaemon.log' ) # App log

#reviewDir = globalOptions['REVIEW_DIR']

#SCRIPT_LOCATION  = '/TROVARND/RND/DEV/bin/R/TrovaPipe_3.93.6.R'
#SCRIPT_LOCATION  = '/home/palak/isilon/BI-125-trovapipe-structure-modification/DataAnalysisWrapper_1604v1_0_0.py'
TROVAPIPE_SCRIPT  = os.path.join( globalOptions['TROVAPIPE_BASE'] , globalOptions['TROVAPIPE_SCRIPT'] ) # get trovapipe script location from config file
VERSION = globalOptions['VERSION']

# also going to need to load TROVAPIPE config file
TROVAPIPE_CONFIG = os.path.abspath( os.path.join( os.path.dirname( os.path.realpath(__file__) ), globalOptions['TROVAPIPE_CONFIG'] ))
if not os.path.exists( TROVAPIPE_CONFIG ) :
	msg = str('The TrovaPipe config.ini file "' + TROVAPIPE_CONFIG + '" is missing.  Analysis cannot proceed...')
	tputils.LogAndEmail( msg, 4)
	sys.exit()
#print 'TROVAPIPE CONFIG FILE: ' + TROVAPIPE_CONFIG
tpConfig = ConfigObj(TROVAPIPE_CONFIG, raise_errors=True)
# load TRovaPipe global section
TPglobalOptions = tpConfig['global']
TP_OUTPUT_DIR = TPglobalOptions['outputDir']

''' Serial steps to analyze one run
'''
def Process() :

	# get list of repos
	repositories = tputils.Repositories()
	
	# process list of repos and get dictionary of analyzeable runs
	runDirs = CheckRuns( repositories )
	
	# process dictionary of runs
	if runDirs != None :
		for flowcellID, runDir in runDirs.iteritems():
			full_root_run_path = os.path.realpath( runDir )
			Analyze( full_root_run_path , flowcellID )

	
''' Iterate uniflow NGS runs where status indicates they
    are ready for analysis & return only one ( or None )
'''
def CheckRuns( repositories ) :

	results = tputils.QueryRunsByStatus( limskeys.NGS_RUN_COMPLETE )
	
	runDirs = {}

	for flowcellID , metadata in results.iteritems() :
		if flowcellID != 'null' :
			for repo_path in repositories :
				run_dir = glob.glob( os.path.join( repo_path , '*' + flowcellID ) )
				if len( run_dir ) > 1 :     # Zero is okay, > 1 is NOT okay, 
					message = "ERROR: More than one run exists in the repository with the same " \
					   + "flowcellID: " + flowcellID + " . This is an error condition which must be fixed!\n"
					for dir in run_dir :
						message += dir + '\n'
					tputils.LogAndEmail( message , 2 )
					tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
				elif len( run_dir ) == 1 :
					#return run_dir[ 0 ]  , flowcellID
					runDirs[ flowcellID ] = run_dir[ 0 ]
				else : continue # run is not in this repository
	
	if len(runDirs) > 0:
		return runDirs
	else: return None

''' run trovapipe
    drop flag stating analysis complete or update db state?
'''
def Analyze( run_root , flowcellID ) :
		
	logging.info( "Starting analysis for run: " + run_root )
			
	basecalls_dir = os.path.join( run_root , FASTQ_DIR_SUFFIX )

	# QC file should already be created
	runqc_file = glob.glob( os.path.join( run_root , '*_stats.csv' ) )[0]
	if not os.path.exists( runqc_file ) :
		tputils.LogAndEmail( 'Run QC _stats.csv file is missing from the run folder: ' + run_root , 2 )
		sys.exit()

	# set status of run to analysis in progress
	tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_IN_PROGRESS )
		
	
	# log command line	
	CMD = 'python ' + TROVAPIPE_SCRIPT + ' -i ' + run_root + ' -c ' + TROVAPIPE_CONFIG
	#CMD = 'python ' + TROVAPIPE_SCRIPT + ' -i ' + run_root + ' -c ' + TROVAPIPE_CONFIG + ' --resume'
	print "\nRunning command: " + CMD + "\n"
	tputils.LogAndEmail('Running TrovaPipe: ' + CMD, 0)
	
	# run analysis
	try:
		output = subprocess.check_output(CMD, universal_newlines=True, stderr=subprocess.STDOUT, shell=True)
	except subprocess.CalledProcessError as err:
		msg = "\nERROR: A non-zero exit was returned when running TrovaPipe on run folder: " + run_root + " ...\nRETCODE: " + str(err.returncode) + "\nCMD: " + err.cmd + "\nOUTPUT: " + err.output
		print 'ERROR:',str(err)
		print 'ERROR CODE:',str(err.returncode)
		print 'ERROR CMD:',err.cmd
		print 'ERROR OUTPUT:',err.output
		tputils.LogAndEmail( msg , 4 )
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
		#raise Exception( msg )
		raise
		
	try:
		summary = sorted(glob.glob( os.path.join( TP_OUTPUT_DIR, '*' + flowcellID + '*', '*' + flowcellID + '*_summary.csv' )))[-1]
		stats = sorted(glob.glob( os.path.join( TP_OUTPUT_DIR, '*' + flowcellID + '*', '*' + flowcellID + '*_stats.csv' )))[-1]
		pdf = sorted(glob.glob( os.path.join( TP_OUTPUT_DIR, '*' + flowcellID + '*', '*' + flowcellID + '*_all_plots.pdf' )))[-1]
		
		
		runId = run_root.rstrip(str(os.sep)).split(str(os.sep))[-1]
	
		tputils.UploadRunResultsToUniflow( summary , stats, pdf, flowcellID, runId = runId )
	
	except Exception as detail : # Catch ALL exceptions
		tputils.LogAndEmail( APP_NAME + " crashed: " + str( detail ) + ' ' + traceback.format_exc() , 4 )
		tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
		
	
	## if everything above went ok, set Uniflow state
	#try:
		#tputils.SetUNIFlowState( flowcellID , limskeys.NGS_CLIA_REVIEW )
	#except Exception as detail : # Catch ALL exceptions
		#tputils.LogAndEmail( APP_NAME + " crashed: " + str( detail ) + ' ' + traceback.format_exc() , 4 )
		#tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
		
		
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
		
		if not os.path.exists( TROVAPIPE_SCRIPT ) :
			tputils.LogAndEmail( "ERROR: Error, cannot find the TrovaPipe script: " + TROVAPIPE_SCRIPT , 4 )
			sys.exit()
		else : os.chdir( os.path.dirname( TROVAPIPE_SCRIPT) )
			
		Process()
		
		
	except Exception as detail : # Catch ALL exceptions
		tputils.LogAndEmail( APP_NAME + " crashed: " + str( detail ) + ' ' + traceback.format_exc() , 4 )
