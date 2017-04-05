#!/usr/bin/python

# commented: rem for alt form of RESTful API
#import urllib3.contrib.pyopenssl
#urllib3.contrib.pyopenssl.inject_into_urllib3()
#import requests
#import ssl
#import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append('../')
#from scripts.RunQC import runQC as QC
from scripts.RunQC_illumina import runQC as QC2
import atexit
import logging
import time
import datetime
import traceback
from Keys import Keys as limskeys
import psutil
import subprocess
import glob
import shutil
from Utilities import TrovapipeUtils as tputils
from configobj import ConfigObj
import inspect

# Date: 4/12/16
# Name: Thomas Richardson
# Email: trichardson@trovagene.com
#
# Description: Starts from cron and monitors a MiSeq run respository looking
#              for new runs being copied over from the instruments to the repo.
#
#              1. Queries uniflow for runs with status: pending
#              2. Verfies run copy is complete and sets status to: complete
#
#              Alternatively: Notifies informatics if copies appear to be stuck or
#              unanalyzeable for a signficant period of time.
#
#              Has other features such as ability to prevent a clone of the process
#              etc..

# MODIFICATIONS : 11/1/2016 by Palak Sheth

CONFIG_FILE         = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'TrovaWrapper_config.ini' )

# load config file
if not os.path.exists( CONFIG_FILE ) :
	msg = str('ERROR: The TrovaWrapper config.ini file "' + CONFIG_FILE + '" is missing.  Analysis cannot proceed...')
	tputils.LogAndEmail( msg, 4)
	#logging.critical( msg )
	sys.exit()
#Config = ConfigParser.ConfigParser()
Config = ConfigObj(CONFIG_FILE, raise_errors=True)
# load global section
globalOptions = Config['global']

APP_NAME            = 'CLIA Run Status Daemon'
COPY_COMPLETE_FLAG  = globalOptions['COPY_COMPLETE_FLAG']
FASTQ_DIR_SUFFIX    = os.path.join( os.path.join( 'Data' , 'Intensities' ) , 'BaseCalls' ) # Data/Intensities/Basecalls
LOCK_FILE           = os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'rundaemon.lock.pid' ) # Prevent multiple processes
APP_LOG             = os.path.join( os.path.join( os.path.dirname( os.path.realpath(__file__) ) , 'Log' ) , 'rundaemon.log' ) # App log
DEAD_RUN_DELAY      = float(globalOptions['DEAD_RUN_DELAY']) # 5min pause before warning email is sent
COPY_COMPLETE_DELAY = float(globalOptions['COPY_COMPLETE_DELAY']) # 5min pause before marking copy complete.  Temporary workaround to prevent copy robustness issue
VERSION = globalOptions['VERSION']

TROVAPIPE_SCRIPT_DIR = globalOptions['TROVAPIPE_BASE']
TROVAPIPE_CONFIG = os.path.abspath( os.path.join( os.path.dirname( os.path.realpath(__file__) ), globalOptions['TROVAPIPE_CONFIG'] ))
bypassQC = globalOptions['bypassQC']
if bypassQC.upper() == 'TRUE' or bypassQC == True:
	bypassQC = True
else:
	bypassQC = False


''' Checks for runs ready to be analyzed, when found
    updates UNIFlow with the status
'''
def CheckRuns() :
	
	#get list of run repos to check
	repositories = tputils.Repositories()
	
	# make blank list
	new_analyzeable_runs = list()
	
	# query LIMS and get list of runs that have been queued for sequencing
	results = tputils.QueryRunsByStatus( limskeys.NGS_RUN_PENDING )

	if results != None :
		for flowcellID , metadata in results.iteritems() :
			if flowcellID != 'null' :
				for repo_path in repositories :
					#logging.info( 'Looking at repo ' + repo_path )  
					run_dir = glob.glob( os.path.join( repo_path , '*' + flowcellID ) )
					if len( run_dir ) > 1 :     # Zero is okay, > 1 is NOT okay, 
						message = "ERROR: More than one run exists in the repository with the same " \
						   + "flowcellID. This is an error condition which must be fixed.\n"
						for dir in run_dir :
							message += dir + '\n'
						tputils.LogAndEmail( message , 4 )
						tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
					elif len( run_dir ) == 1 :
						run_dir = run_dir[ 0 ]
						copy_complete_flag_path = os.path.join( run_dir , globalOptions['COPY_COMPLETE_FLAG'] )
						sampleSheet = os.path.join( run_dir, 'SampleSheet.csv' ) 
						#if os.path.exists( copy_complete_flag_path ) and Is_OldEnough( copy_complete_flag_path ) : # If so we look for the illumina run copy complete flag
						if os.path.exists( copy_complete_flag_path ) and os.path.exists( sampleSheet ) and Is_OldEnough( copy_complete_flag_path ): # If so we look for the illumina run copy complete flag
							fastq_dir = os.path.join( run_dir , FASTQ_DIR_SUFFIX )
							if os.path.isdir( fastq_dir ) :                                        # We make sure it's fastq dir has appeared
								#analyzable , message = QC.check_run( fastq_dir )                   # If it's there we double check the data exists as per sample sheet
								analyzable , message = QC2.check_run( basecalls_dir=fastq_dir, sampleSheet=sampleSheet, configFile = TROVAPIPE_CONFIG , working_dir=os.path.dirname( run_dir ), toolVersion=VERSION )
								# If analyzable update UNIFlow state to RUN_COMPLETE
								if analyzable:								
									tputils.SetUNIFlowState( flowcellID , limskeys.NGS_RUN_COMPLETE )
									new_analyzeable_runs.append( run_dir )
								else :
									# if bypassQC=True then continue
									if bypassQC and not analyzable:
										msg = 'WARNING: Run QC failed for flowcellID ' + flowcellID + ' but continuing anyway due to \'bypassQC=True\' in config file\n\tMESSAGE: ' + message 
										tputils.LogAndEmail( msg , 2 )
										tputils.SetUNIFlowState( flowcellID , limskeys.NGS_RUN_COMPLETE )
										new_analyzeable_runs.append( run_dir )
									
									# If the flag is recent wait a bit
									elif not Is_Old( copy_complete_flag_path ) : continue  
									# Or else log and send a warning email
									else:
										message = "WARNING: Cannot analyze: " + run_dir \
											+ " The copy complete flag exists but the data" \
											+ " cannot be analyzed: " + copy_complete_flag_path \
											+ " Detail: " + message
										tputils.LogAndEmail( message , 2 )
										tputils.SetUNIFlowState( flowcellID , limskeys.NGS_ANALYSIS_ERROR )
					else : continue # Run is not in this repo
				
	total = len( new_analyzeable_runs )
	
	tputils.LogAndEmail( "Found " + str( total ) + " new runs ready for analysis." , 0 )
	
''' Temporary workaround to solve a run copy robustness
    issue.  We'll wait 1.5 hours after we see the flag 
	that states the copy is complete, just in case it's not
'''
def Is_OldEnough( copy_complete_file ) :
	now = time.time()
	file_creation = os.path.getctime( copy_complete_file )
	if (now - file_creation) > float(globalOptions['COPY_COMPLETE_DELAY']) :
		return True
	return False
		
''' Checks to see if a run may be stuck
    in an unanalyzeable state.  If the copy 
	complete flag is more than 1 hour old it is
	considered stuck.
'''
def Is_Old( copy_complete_file ) :
	now = time.time()
	file_creation = os.path.getctime( copy_complete_file )
	if (now - file_creation) > float(globalOptions['DEAD_RUN_DELAY']) :
		return True
	return False
	
''''''''''''''''''''''''
''' Main	
'''''''''''''''''''''
if __name__=="__main__" :
	try :
		
		tputils.ArchiveLog( APP_LOG )
		logging.basicConfig( filename=APP_LOG , level=logging.DEBUG )
		logging.info( 'Starting ' + APP_NAME + ' version:' + VERSION + ', ' + datetime.datetime.fromtimestamp( time.time() ).strftime( '%Y-%m-%d %H:%M:%S' ) )  

		tputils.NoClone( LOCK_FILE )                              # Kill process and don't remove lock if it's a clone
		atexit.register( tputils.CleanUp , LOCK_FILE , APP_NAME ) # Kill the lock at exit

		if not os.path.exists( TROVAPIPE_SCRIPT_DIR ) :
			tputils.LogAndEmail( "EERROR: cannot find the TrovaPipe script dir: " + TROVAPIPE_SCRIPT_DIR , 4 )
			sys.exit()
		else : os.chdir( TROVAPIPE_SCRIPT_DIR )
		
		CheckRuns()
		
	except Exception as detail : # Catch ALL exceptions
		tputils.LogAndEmail( APP_NAME + " crashed: " + str( detail ) + ' ' + traceback.format_exc() , 4 )
		
