#!/usr/bin/python

from __future__ import division
#class flushfile(object):
	#def __init__(self, f):
		#self.f = f
	#def write(self, x):
		#self.f.write(x)
		#self.f.flush()
import sys, os
#sys.stdout = flushfile(sys.stdout)
#sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
import subprocess
import getopt
import glob
import inspect

VERSION = 'ReadsProcessingModule 1.0.0'

def runReadsProcessing ( basecalls_dir, samplesheet_file, config_file, sge, force, working_dir, toolVersion, environment, mode ) :
	# runs perl reads processing script given inputs
	
	print 'ReadsProcessing module version is " ' + VERSION + ' "\n'
	
	# get current install dir
	myPath = os.path.realpath(__file__)
	cwd = os.path.dirname(os.path.abspath(myPath))
	
	# extract runid from input location (basecalls_dir, always /<runid>/Data/Intensities/BaseCalls/ so get fourth from last)
	basecalls_dir = basecalls_dir.rstrip(os.sep)
	runId = basecalls_dir.split(os.sep)[-4]
	
	# log file for readsProcessing module
	if not os.path.exists(os.path.join(working_dir, runId)) :
		os.makedirs(os.path.join(working_dir, runId))
	#logFile = os.path.join(working_dir, runId)
	logFile = os.path.join(os.path.join(working_dir, runId), runId + "_readsProcessing_log.txt")
	
	## Usage: perl generate_RAWCOUNTS_SGE.pl --basecallsDir /path/to/run/Data/Intensities/BaseCalls --samplesheet /path/to/SampleSheet.csv --config /path/to/config.ini [--sge flag to use SGE scheduler] [--force force overwrite of output directory] [--help]
	cmd = [ 'perl', os.path.join(cwd,'generate_RAWCOUNTS_SGE.pl') , '--basecallsDir' , basecalls_dir , '--samplesheet' , samplesheet_file , '--config' , config_file, '--tool', toolVersion, '--environment', environment, '--mode', mode ]
	if sge == True or sge == "True" :
		cmd = cmd + ['--sge']
	if force == True or force == "True" :
		cmd = cmd + ['--force']
	cmd = cmd + ['2>&1 | tee', logFile]
	cmd = ' '.join(cmd)
	msg = ''
	try:
		print "\t" + 'Running command:', str(cmd)
		print "\nThis process may take up to 2 hours (or maybe even more). Please be patient...\n"
		output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT, shell=True)
		msg = output
	except subprocess.CalledProcessError as err:
		msg = "\nRETCODE: " + str(err.returncode) + "\nCMD: " + err.cmd + "\nOUTPUT: " + err.output
		print 'ERROR:',str(err)
		print 'ERROR CODE:',str(err.returncode)
		print 'ERROR CMD:',err.cmd
		print 'ERROR OUTPUT:',err.output
		raise Exception( 'ERROR: readsProcessing module error! Check log file: ' + logFile + ' MSG: ' + msg )
	expectedOutfiles = glob.glob(os.path.join(working_dir, runId, str(runId + '_RAWCOUNTS.csv')))
	if len(expectedOutfiles) > 0 :
		return 0
	else :
		raise Exception('ERROR: expected output file from readsProcressing module not found! See log file for further info: ' + logFile + " MSG: \n" + msg)
		return 1
# for use as a script
if __name__ == "__main__":
	# parse command line options
	# initialize basic command line options
	options = {}
	options['basecalls_dir'] = ''
	options['samplesheet_file'] = ''
	options['config_file'] = ''
	options['sge'] = False
	options['force'] = False
	options['workingDir'] = ''

	opts, remainder = getopt.getopt(sys.argv[1:],	"sfb:s:c:w",
											[   "sge",
												"force",
												"basecallsDir=",
												"samplesheet=",
												"workingDir=",
												"config="])
	# parse opts
	for opt, arg in opts:
		if opt in ('-s', "--sge"):
			options['sge'] = True
		elif opt in ('-f', "--force"):
			options['force'] = True
		elif opt in ("-b", "--basecallsDir"):
			options['basecallsDir'] = arg
		elif opt in ("-s", "--samplesheet"):
			options['samplesheet'] = arg
		elif opt in ("-c", "--config"):
			options['config'] = arg
		elif opt in ("-w", "--workingDir"):
			options['workingDir'] = arg
	
	retcode = runReadsProcessing(options['basecallsDir'], options['samplesheet'], options['config'], options['sge'], options['force'], options['workingDir'])
	print "\n" + 'Return code: ' + str(retcode) + "\n\n"
