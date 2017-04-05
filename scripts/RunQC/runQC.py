#!/usr/bin/env python
import sys
import glob
import os
import Utilities.FileUtils
import RunQualityInfo.MiSeqRunQualityInfo as MiSeqQuality
import configuration
import logging

VERSION = 'RunQCReporter 1.0'

# Run this code to sanity check the experiment and
# to collect sample information
def check_run( basecalls_dir, working_dir, toolVersion ) :
	
	print 'Sequencing QC version is " ' + VERSION + ' "'
	
	# Check if basecalls dir exists
	ok , msg = sanity( basecalls_dir )
	if not ok : return False , msg # no data to analyze
	
	# Get sample sheet information
	config = configuration.Config( basecalls_dir )
	if len( config.sampleInfoDictionary ) == 0 : return False , "No Sample Sheet" # No info about data
	
	# clean up any old stats files
	if os.path.exists ( os.path.join( working_dir , config.runID, config.runID + "_stats.csv" ) ) :
		os.remove( os.path.join( working_dir , config.runID, config.runID + "_stats.csv" ) )
	
	# Plug in new instruments here
	if config.instrument_type == "miseq" :
		runQualityInfo = MiSeqQuality.MiSeqRunQualityInfo( config )
	#elif instrument_type == "hiseq" :

	runQualityInfo.writeReport2( config , toolVersion, working_dir )
	
	
	
	
	
	
	
	
	
	
	
	
	
	return runQualityInfo.OK() # True if data are usable


# Check before doing anything
def sanity( basecalls_dir ) :
	exists , message = Utilities.FileUtils.exists( basecalls_dir )
	return exists , message 
	

		

