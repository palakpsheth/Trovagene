#!/usr/bin/python

# this wrapper will reside in each environment subfolder (DEV, QA, PROD). Config file in each environment should be changed with each deployment

from __future__ import division
class flushfile(object):
	def __init__(self, f):
		self.f = f
	def write(self, x):
		self.f.write(x)
		self.f.flush()
class multifile(object):
    def __init__(self, files):
        self._files = files
    def __getattr__(self, attr, *args):
        return self._wrap(attr, *args)
    def _wrap(self, attr, *args):
        def g(*a, **kw):
            for f in self._files:
                res = getattr(f, attr, *args)(*a, **kw)
            return res
        return g
import sys, os
PID = os.getpid()
sys.path.insert(0, os.path.join( os.path.dirname(__file__), 'bin' ) )
import subprocess
import traceback
import getopt
import datetime
import inspect
import re
import pandas as pd
#import ConfigParser
from configobj import ConfigObj
import imp
import time
from datetime import datetime
import socket
import getpass
import glob, operator
import shutil

# capture stdout and stderr to log files
LOG_BASE = '/mnt/rnd/home/trovapipe/TrovaPipeLogs/'
if not os.path.exists( LOG_BASE ) : os.makedirs( LOG_BASE )
sys.stdout = multifile( [ sys.stdout, open( os.path.join( LOG_BASE, str(PID) + "_stdout_log.txt" ), 'w' ) ])
sys.stdout = flushfile(sys.stdout)
sys.stderr = multifile( [ sys.stderr, open( os.path.join( LOG_BASE, str(PID) + "_stderr_log.txt" ), 'w' ) ])
sys.stderr = flushfile(sys.stderr)

# import error code modules
import DataAnalysisWrapperErrors as dawe


def Usage():
	filename = os.path.basename(__file__)
	print "USAGE: python " + filename + " -i <input run folder> -c <configuration file> [--force overwrite workingDir results] [-m <mode DEV, QA, PROD>] [-e <environment CLIA, RND>] [--sge flag to use SGE]" + "\n"

def main(argv):
	try:
		print
		print '###############################################'
		print '############### TROVAGENE, INC. ###############'
		print '############# TROVAPIPE ANALYSIS ##############'
		print '###############################################'
		print 
		
		# print starting command
		print 'COMMAND: python ' + " ".join(sys.argv)
		print 'PID: ' + str(PID)
		print
		
		# print hostname
		print 'HOSTNAME: ' + socket.gethostname()
		print
		
		# print username
		print 'USERNAME: ' + getpass.getuser() 
		print
		
		# print current time
		start = time.time()
		print 'Start time: ' + str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
		print
		
		# get current install dir
		#myPath = inspect.getsourcefile(lambda:0)
		myPath = os.path.realpath(__file__)
		cwd = os.path.dirname(os.path.abspath(myPath))
		
		# print TrovaPipe version
		print 'TrovaPipe version is " ' + getVersion(cwd) + ' "'
		print		
	
		# get defaults
		defaults = get_defaults(cwd)
		
		# parse given options and get runid from required option basecalls_dir
		options = parse_cmdLine_options(argv, defaults, cwd)
		
		# parse and read config file
		options, ConfigObject = parse_config_file(options)
		
		# check if working_dir exists
		if os.path.exists( os.path.join( options['workingDir'], options['runId'] ) ):
			if options['force'] == True :
				print '\tWARNING: Run specific directory ' + os.path.join( options['workingDir'], options['runId'] ) + ' already exists but will be overwritten due to --force!'
				print
			elif options['resume'] == True :
				print '\tWARNING: Run specific directory ' + os.path.join( options['workingDir'], options['runId'] ) + ' already exists but will try to resume due to --resume!'
				print
			else:
				raise dawe.PathError(1214)
		
		##############################################################################
		### import Environment-specific modules ###
		sys.path.append(options['install_dir'])
		# import SSV module
		from scripts.sampleSheetValidator import SampleSheetValidator as ssv
		# import RunQC module
		#from scripts.RunQC import runQC as qc
		from scripts.RunQC_illumina import runQC as qc2
		# import readsProcessing module
		from scripts.readsProcessing import runReadsProcessing as rp
		# import algorithims module
		from scripts.data_analysis import runDataAnalysis as da
		# import output formatter module
		from scripts.output_formatter import outputFormatter as of
		#############################################################################
			
		##### DEBUG #####
		print	
		print "Using [global] options:"
		for key in options:
			print "\t" + "--" + key + " : " + str(options[key])
		print
		#################
		
		### STEP 1: Run SampleSheet Validator
		
		print '###################'
		print '##### STAGE 1 #####'
		print '###################'
		print
		
		sampleSheet = options['samplesheet']
		runId = options['runId']
		
		if not os.path.exists( os.path.join( options['workingDir'], options['runId'] )):
			os.makedirs( os.path.join( options['workingDir'], options['runId'] ))
		ss_valid = os.path.join( options['workingDir'], options['runId'], options['runId'] + '_SampleSheet_Used.csv' )
		
		### IF TRYING TO RESUME SKIP THIS STEP ###
		doStage1 = True
		#if options['resume'] == True:
			#print 'Trying to resume runId: ' + options['runId'] + " . Looking for validated SampleSheet: " + ss_valid + " ..."
			#if os.path.exists( ss_valid ):
				#print "\tFound validated SampleSheet: " + ss_valid
				#doStage1 = False
				#sampleSheet = ss_valid
			#else:
				#print "\tWARNING: Could not find validated SampleSheet: " + ss_valid + " . Restarting stage..."
				#doStage1 = True
			#print
			
		# IF STAGE 1 needs to be done
		if doStage1 == True:
			try:
				retcode = ssv.runSSV( basecalls_dir=options['input_dir'], sample_sheet=options['samplesheet'], runid=options['runId'], ss_outfile=ss_valid, ss_infer_info=options['ss_infer_info'] )
				# check to ensure that the sampleSheet file exists, and set global variable to be used later
				path = os.path.join( options['workingDir'], runId ) + os.sep + runId + '*_SampleSheet_Used.csv'
				sampleSheet = glob.glob( path )
				if not len(sampleSheet) == 0 :
					sampleSheet = sampleSheet[0]
				else:
					raise dawe.SSValidatorError(1318)
				if not os.path.exists( sampleSheet ) :
					raise dawe.SSValidatorError(1318)
				
			except Exception as err:
				if ( options['environ'].upper() == "RND" ) :
					print "WARNING %d: %s" % (err.args[0], err.em[err.args[0]])
					print
					print 'SampleSheet Validation module FAILED but will try to continue anyway because running in \'RND\' environment. I would not expect things to go well from here...'
					shutil.copyfile( sampleSheet, ss_valid )
					sampleSheet = ss_valid
				else :
					raise
		
		print
		
		### STEP 2: Run Sequencing run QC
		
		print '###################'
		print '##### STAGE 2 #####'
		print '###################'
		print
		
		stats_file = ''
		
		### IF TRYING TO RESUME SKIP THIS STEP ###
		doStage2 = True
		#if options['resume'] == True:
			#print 'Trying to resume runId: ' + options['runId'] + " . Looking for Run QC stats file in: " + os.path.join( options['workingDir;'], options['runId'] ) + " ..."
			#foundFiles = glob.glob( os.path.join( options['workingDir;'], options['runId'], options['runId'] + '*_stats.csv' ))
			#if len(foundFiles) > 0:
				#stats_file = foundFiles[0]
				#print "\tFound Run QC stats file: " + stats_file
				#doStage2 = False
			#else:
				#print "\tWARNING: Could not find Run QC stats file in directory: " + os.path.join( options['workingDir;'], options['runId']) + " . Restarting stage..."
				#doStage2 = True
			#print
			
		# IF STAGE 2 needs to be done
		if doStage2 == True:
			try:
				is_pass, message = qc2.check_run( basecalls_dir=options['input_dir'], working_dir=options['workingDir'], toolVersion=options['version'], sampleSheet=sampleSheet, configFile=options['config_file'] )
				if is_pass :
					print "\t" + 'Sequencing QC status: PASS'
					#print "\t" + options['runId'] + " passes sequencing run QC!\n"
				elif not is_pass :
					#print 'bypassQC: ' + str(options['bypassQC'])
					if options['bypassQC'] == False or options['bypassQC'].upper() == 'FALSE':
						print "\t" + 'Sequencing QC status: FAIL'
						print "\t" + options['runId'] + " FAILS sequencing run QC: " + message
						raise dawe.SequencingQcError(1601)
					else:
						print "\t" + 'Sequencing QC status: FAIL but continuing anyway due to \'bypassQC=True\' in config file'
						print "\t" + 'Message: ' + message
					
				# check to ensure that the stats file exists, and set global variable to be used later
				path = os.path.join( options['workingDir'], runId ) + os.sep + runId + '*_stats.csv'
				stats_file = glob.glob( path )
				if not len(stats_file) == 0 :
					stats_file = stats_file[0]
				else:
					raise dawe.SequencingQcError(1602)
				if not os.path.exists( stats_file ) :
					raise dawe.SequencingQcError(1602)
			
			except Exception as err:
				if ( options['environ'].upper() == "RND" ) :
					print "WARNING %s: %s" % (err.args[0], str(err))
					print
					print 'Sequencing QC module FAILED but will try to continue anyway because running in \'RND\' environment. Things are getting worse...'
				else :
					raise
		
		print
		
		### STEP 3: Run readsProcessing module
		
		print '###################'
		print '##### STAGE 3 #####'
		print '###################'
		print
		
		RAWCOUNTS_file = ''
		
		### IF TRYING TO RESUME SKIP THIS STEP ###
		doStage3 = True
		if options['resume'] == True:
			print 'Trying to resume runId: ' + options['runId'] + " . Looking for reads processing RAWCOUNTS file in: " + os.path.join( options['workingDir'], options['runId'] ) + " ..."
			foundFiles = glob.glob( os.path.join( options['workingDir'], options['runId'], options['runId'] + '*_RAWCOUNTS.csv' ))
			if len(foundFiles) > 0:
				RAWCOUNTS_file = foundFiles[0]
				print "\tFound reads processing RAWCOUNTS file: " + RAWCOUNTS_file
				doStage3 = False
			else:
				print "\tWARNING: Could not find reads processing RAWCOUNTS file in directory: " + os.path.join( options['workingDir'], options['runId']) + " . Restarting stage..."
				doStage3 = True
			print
			
		# IF STAGE 3 needs to be done
		if doStage3 == True:
		
			#def runReadsProcessing ( basecalls_dir, samplesheet_file, config_file, sge, force, working_dir, options['version'] ) :
			force = True
			#retcode = 1
			retcode = rp.runReadsProcessing( options['input_dir'], sampleSheet, options['config_file'], options['sge'], force, options['workingDir'], options['version'], options['environ'], options['mode'] )
			if not retcode == 0 :
				raise dawe.ReadsProcessingError(1701)
			else:
				print
				print "\t" + 'Reads Processing complete!' + "\n"
		
			# check to ensure that the RAWCOUNTS file exists, and set global variable to be used later
			#print 'RUNID: ' + runId
			path = os.path.join( options['workingDir'], runId ) + os.sep + runId + '*_RAWCOUNTS.csv'
			#print 'PATH: ' + path
			RAWCOUNTS_file = glob.glob( path )
			if not len(RAWCOUNTS_file) == 0:
				RAWCOUNTS_file = RAWCOUNTS_file[0]
			else:
				raise dawe.ReadsProcessingError(1702)
			#print 'RAWCOUNTS FILE: ' + str(RAWCOUNTS_file)
			#print RAWCOUNTS_file
			if not os.path.exists( RAWCOUNTS_file ) :
				raise dawe.ReadsProcessingError(1702)
		
		print
		
		### STEP 4: Run algorithims module
		
		print '###################'
		print '##### STAGE 4 #####'
		print '###################'
		print
		
		summary_file = ''
		pdf_file = ''

		try:
			retcode = da.runDataAnalysis( runId, options['config_file'], RAWCOUNTS_file, stats_file, options['workingDir'] )
			if not retcode == 0 :
				raise dawe.DataAnalysisError(1801)
			else:
				print
				print "\t" + 'Data Analysis complete!' + "\n"
		
			# check to ensure that the summary file exists, and set global variable to be used later
			path = os.path.join( options['workingDir'], runId ) + os.sep + runId + '*_summary.csv'
			summary_file = glob.glob( path )
			if not len(summary_file) == 0:
				summary_file = summary_file[0]
			else:
				raise dawe.DataAnalysisError(1802)
			if not os.path.exists( summary_file ) :
				raise dawe.DataAnalysisError(1802)
			
			# check to ensure that the pdf file exists, and set global variable to be used later
			path = os.path.join( options['workingDir'], runId ) + os.sep + runId + '*_all_plots.pdf'
			pdf_file = glob.glob( path )
			if not len(pdf_file) == 0:
				pdf_file = pdf_file[0]
			else:
				raise dawe.DataAnalysisError(1803)
			if not os.path.exists( pdf_file ) :
				raise dawe.DataAnalysisError(1803)
				
		except Exception as err:
			if ( options['environ'].upper() == "RND" ) :
				print "WARNING %s: %s" % (err.args[0], err.em[err.args[0]])
				print
				print 'Data Analysis module FAILED but will try to continue anyway because running in \'RND\' environment...'
			else :
				raise
				
		print
		
		### STEP 5: Output format module
		
		print '###################'
		print '##### STAGE 5 #####'
		print '###################'
		print
	
		# couple possibilities exist for outputting
		
		#print 'RUNID: ' + runId
		#print 'OUTPUT DIR: ' + options['outputDir']
		#print 'SAMPLESHEET FILE: ' + sampleSheet
		#print 'STATS FILE: ' + stats_file
		#print 'RAWCOUNTS FILE: ' + RAWCOUNTS_file
		#print 'PDF FILE: ' + pdf_file
		#print 'SUMMARY FILE: ' + summary_file
		#print
	
		# run outputFormatter module
		retcode = of.runOutputFormatter( sampleSheet, stats_file, RAWCOUNTS_file, pdf_file, summary_file, options['outputDir'], runId )
	
		if retcode != 0:
			raise(dawe.OutputFormatterError(1901))
	
		print
		
	
#######################################################################################################################################################################################################################################################

		print '###################'
		print '##### SUMMARY #####'
		print '###################'
		print

		# print out elapsed time
		print
		print 'End time: ' + str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
		print
		print
		end = time.time()
		hours, rem = divmod(end-start, 3600)
		minutes, seconds = divmod(rem, 60)
		print("Total elapsed time: {:0>2} hours, {:0>2} minutes, and {:05.2f} seconds".format(int(hours),int(minutes),seconds))
		print
	
		return 0
		
	except (dawe.UnknownOSError, dawe.OptionError, dawe.PathError, dawe.SSValidatorError, dawe.PipelineError, dawe.ConfigFileError, dawe.SequencingQcError, dawe.ReadsProcessingError, dawe.DataAnalysisError, dawe.OutputFormatterError) as err:
		print "Error %d: %s" % (err.args[0], err.em[err.args[0]])
		print

		#print 'Printing error log to results directory:',tp_results_dir
		# save error message in error log file in results_dir (hopefully by this point tp_results_dir, trovapipe_ver, and runid have all been populated
		#f = open(os.path.join(tp_results_dir,'error_log_'+trovapipe_ver+'_'+runid+'_'+datetime.datetime.now().strftime("%y%m%d%H%M%S")+'.txt'), 'w', 0)
		#f.write("Error %d: %s" % (err.args[0], err.em[err.args[0]]))
		#f.close()

		return err.args[0]
		
	except:
		print 'Unexpected error:',sys.exc_info()[0]
		print 'Traceback:',sys.exc_info()[2], traceback.format_exc()
		print

		#print 'Printing error log to results directory:',tp_results_dir
		# save error message in error log file in results_dir (hopefully by this point tp_results_dir, trovapipe_ver, and runid have all been populated
		#f = open(os.path.join(tp_results_dir,'error_log_'+trovapipe_ver+'_'+runid+'_'+datetime.datetime.now().strftime("%y%m%d%H%M%S")+'.txt'), 'w', 0)
		#f.write(traceback.format_exc())
		#f.close()

		return 1


def get_defaults(cwd):

	defaults = {}
	
	# arbitrary installation directory (where this script resides)
	defaults['install_dir'] = cwd
	
	# defaults to RND and DEV
	if "CLIA" in defaults['install_dir'] :
		defaults['env'] = "CLIA"
	else :
		defaults['env'] = "RND"
	
	if "PROD" in defaults['install_dir'] :
		defaults['mode'] = "PROD"
	elif "QA" in defaults['install_dir'] :
		defaults['mode'] = "QA"
	else :
		defaults['mode'] = "DEV"

	defaults['config_file'] = os.path.join(cwd,'config.ini')
	
	#defaults['ss_infer_info'] = 0		# put burden of providing correct sample sheet on user, but allow for backward compatibility (should eventually be solved with LIMS)
	defaults['ss_infer_info'] = 1		# agreed to use inference for now until LIMS can provide validation
	if defaults['env'] == 'CLIA' :
		defaults['ss_infer_info'] = 0

	if (sys.platform == 'linux2'):
		defaults['workingDir'] = cwd
		defaults['outputDir'] = cwd
	else:
		raise dawe.UnknownOSError(1001)
		#print "Unsupported OS"

	return defaults

def parse_cmdLine_options(argv, defaults, cwd):
	
	# initialize basic command line options
	options = {}
	options['config_file'] = defaults['config_file']
	options['input_dir'] = ''
	options['runId'] = ''
	options['ss_infer_info'] = defaults['ss_infer_info']
	options['mode'] = defaults['mode']
	options['environ'] = defaults['env']
	options['version'] = getVersion(cwd)
	options['sge'] = False
	options['force'] = False
	#options['bypassQC'] = False
	options['resume'] = False
	
	try:
		opts, remainder = getopt.getopt(argv,   "hsbfi:c:m:e:r",
											[   "help",
												"sge",
												"bypassQC",
												"force",
												"input_dir=",
												"config_file=",
												"mode=",
												"environ=",
												"resume"])
	except getopt.GetoptError as err:
		# show usage
		Usage()
		print 'ERROR: ',str(err)
		raise dawe.OptionError(1101)
		
	# parse opts
	for opt, arg in opts:
		if opt in ('-h', "--help"):
			Usage()
			sys.exit(0)
		elif opt in ("-i", "--input_dir"):
			options['input_dir'] = arg
		elif opt in ("-c", "--config_file"):
			options['config_file'] = arg
		elif opt in ("-m", "--mode"):
			options['mode'] = arg
		elif opt in ("-e", "--environ"):
			options['environ'] = arg
		elif opt in ("-s", "--sge"):
			options['sge'] = True
		elif opt in ("-f", "--force"):
			options['force'] = True
		elif opt in ("-r", "--resume"):
			options['resume'] = True
	
	# enforce minimal requirements
	
	# input dir
	if (options['input_dir'] == ''):
		Usage()
		raise dawe.OptionError(1102)
	else:
		# enforce for consistent indexing when checking form (next)
		options['input_dir'] = os.path.abspath(options['input_dir'])
		print 'Input directory is "', options['input_dir'], '"'

	# check form of input_dir (should be .../<runid>/Data/Intensities/BaseCalls/)
	if ( len(options['input_dir'].split(os.sep)) < 4 or (options['input_dir'].split(os.sep)[-3] != 'Data') or (options['input_dir'].split(os.sep)[-2] != 'Intensities') or (options['input_dir'].split(os.sep)[-1] != 'BaseCalls') ):
		if (re.search('^[0-9]{6}_M[0-9]{5}_[0-9]{4}_[0-9]{9}-[A-Z0-9]{5}[^'+os.sep+']*$', options['input_dir'].split(os.sep)[-1])):
			# last dir was appropriately formatted runid, so change input_dir accordingly
			options['input_dir'] = os.path.abspath(os.path.join(options['input_dir'],'Data','Intensities','BaseCalls'))
			options['runId'] = options['input_dir'].split(os.sep)[-4]
		else:
			raise dawe.OptionError(1103)
	else:
		# extract runid from input location (input_dir, always /<runid>/Data/Intensities/BaseCalls/ so get fourth from last)
		options['runId'] = options['input_dir'].split(os.sep)[-4]
	
	options['irunid'] = options['runId'][:34]
	
	if not (re.search('^[0-9]{6}_M[0-9]{5}_[0-9]{4}_[0-9]{9}-[A-Z0-9]{5}[^'+os.sep+']*$', options['runId'])):
		raise dawe.OptionError(1104)
	
	# config file	
	if options['config_file'] == '' or not os.path.exists( options['config_file'] ):
		options['config_file'] = defaults['config_file']
		#raise dawe.OptionError(1105)
	else:
		# enforce for consistent indexing when checking form (next)
		options['config_file'] = os.path.abspath(options['config_file'])
	print 'Configuration file is "', options['config_file'], '"'
	
	# set install_dir
	#options['install_dir'] = os.path.join( defaults['install_dir'], options['mode'] )
	options['install_dir'] = os.path.join( defaults['install_dir'] )
	
	# set samplesheet
	options['samplesheet'] = os.path.join( options['input_dir'].split('/Data/Intensities/BaseCalls')[ 0 ], 'SampleSheet.csv' )
	if not os.path.exists( options['samplesheet'] ):
		raise dawe.PathError(1213)
		
	return options

def parse_config_file(options):
	#Config = ConfigParser.ConfigParser()
	#Config.read(options['config_file'])
	Config = ConfigObj(options['config_file'], raise_errors=True)
	#sections = Config.sections()
	
	# parse global options
	try:
		#options['cores'] = Config.get('global', 'cores')
		#options['jobs'] = Config.get('global', 'jobs')
		#options['wrapperQueue'] = Config.get('global', 'wrapperQueue')
		#options['processQueue'] = Config.get('global', 'processQueue')
		#options['pe'] = Config.get('global', 'pe')
		#options['working_dir'] = Config.get('global', 'working_dir')
		#options['output_dir'] = Config.get('global', 'output_dir')
		
		globalSection = Config['global']
		for key, value in globalSection.iteritems():
			#print "Key: " + key + " Value: " + value
			options[key] = value
		
		#options['cores'] = Config['global']['cores']
		#options['jobs'] = Config['global']['jobs']
		#options['wrapperQueue'] = Config['global']['wrapperQueue']
		#options['processQueue'] = Config['global']['processQueue']
		#options['pe'] = Config['global']['pe']
		#options['working_dir'] = Config['global']['workingDir']
		#options['output_dir'] = Config['global']['outputDir']
	except:
		raise dawe.ConfigFileError(1501)
		
	print 'Working directory is " ' + options['workingDir'] + ' "'
	print 'Output directory is " ' + options['outputDir'] + ' "'
	
	return options, Config

def getVersion(cwd):
	gitVersion = str.strip(subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=cwd))
	version = "TrovaPipe_v6.0.0." + gitVersion
	return version

if __name__ == "__main__":
	#print getVersion()
	sys.exit(main(sys.argv[1:]))
	
