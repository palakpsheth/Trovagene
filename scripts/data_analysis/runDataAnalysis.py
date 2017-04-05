#!/usr/bin/python

from __future__ import division
import sys, os
import subprocess
import getopt
import glob
import inspect
import re

VERSION = 'DataAnalysisModule 1.0.0'

def checkOutputForWarnings( output ):
	print
	# output retruned from subprocess call is a byte string
	output = output.split("\n")
	for line in output:
		line.rstrip()
		if "WARNING" in line:
			print "\t" + line

def runDataAnalysis ( runId, config_file, RAWCOUNTS_file, stats_file, working_dir ) :
	# runs R data analysis script given inputs
	
	print 'DataAnalysis module version is " ' + VERSION + ' "\n'
	
	# get current dir, which also contains all R scripts for data analysis
	myPath = os.path.realpath(__file__)
	cwd = os.path.dirname(os.path.abspath(myPath))
	os.chdir( cwd )
	
	# log file for DataAnalysis module
	if not os.path.exists(os.path.join(working_dir, runId)) :
		os.makedirs(os.path.join(working_dir, runId))
	logFile = os.path.join(os.path.join(working_dir, runId), runId + "_data_analysis_log.txt")
	
	## Usage: run_data_analysis.r --runid <runid> --config_filepath /path/to/config.ini --da_dir /path/to/scripts/data_analysis/ --rawcounts_filepath /path/to/<runid>_RAWCOUNTS.csv --stats_filepath /path/to/<runid>_stats.csv --output_dir /path/to/output_dir
	cmd = [ os.path.join(cwd,'run_data_analysis.r'), '--runid', runId, '--config_filepath' , config_file, '--da_dir', cwd, '--rawcounts_filepath', RAWCOUNTS_file, '--stats_filepath', stats_file, '--output_dir', os.path.join(working_dir, runId) ]
	cmd = cmd + ['2>&1 | tee', logFile]
	cmd = ' '.join(cmd)
	try:
		print "\t" + 'Running command:', str(cmd)
		output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT, shell=True)
		checkOutputForWarnings( output )
	except subprocess.CalledProcessError as err:
		msg = "\nRETCODE: " + str(err.returncode) + "\nCMD: " + err.cmd + "\nOUTPUT: " + err.output
		print 'ERROR:',str(err)
		print 'ERROR CODE:',str(err.returncode)
		print 'ERROR CMD:',err.cmd
		print 'ERROR OUTPUT:',err.output
		raise Exception( 'ERROR: DataAnalysis module error! Check log file: ' + logFile + ' MSG: ' + msg )
	expected_summary_file = glob.glob(os.path.join(working_dir, runId, str(runId + '_summary.csv')))
	expected_stats_file = glob.glob(os.path.join(working_dir, runId, str(runId + '_stats.csv')))
	expected_plots_file = glob.glob(os.path.join(working_dir, runId, str(runId + '_all_plots.pdf')))
	if (len(expected_summary_file) == 1 and len(expected_stats_file) == 1 and len(expected_plots_file) == 1) :
		return 0
	else :
		print('ERROR: expected output file from DataAnalysis module not found! See log file for further info: ' + logFile + "\n" + "\nMESSAGE: " + output)
		return 1
# for use as a script
if __name__ == "__main__":
	# parse command line options
	# initialize basic command line options
	options = {}
	options['runId'] = ''
	options['config_file'] = ''
	options['RAWCOUNTS_file'] = ''
	options['stats_file'] = ''
	options['working_dir'] = ''

	opts, remainder = getopt.getopt(sys.argv[1:],	"r:c:i:s:w:",
											[   "runId=",
												"config_file=",
												"RAWCOUNTS_file=",
												"stats_file=",
												"working_dir="])
	# parse opts
	for opt, arg in opts:
		if opt in ("-r", "--runId"):
			options['runId'] = arg
		elif opt in ("-c", "--config_file"):
			options['config_file'] = arg
		elif opt in ("-i", "--RAWCOUNTS_file"):
			options['RAWCOUNTS_file'] = arg
		elif opt in ("-s", "--stats_file"):
			options['stats_file'] = arg
		elif opt in ("-w", "--working_dir"):
			options['working_dir'] = arg
	
	retcode = runDataAnalysis(options['runId'], options['config_file'], options['RAWCOUNTS_file'], options['stats_file'], options['working_dir'])
	print "\n" + 'Return code: ' + str(retcode) + "\n\n"
