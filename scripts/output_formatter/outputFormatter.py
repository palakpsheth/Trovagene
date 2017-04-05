#!/usr/bin/python

import os, sys
import pandas as pd
import numpy as np
import time
import shutil
import csv

# import error code modules
import DataAnalysisWrapperErrors as dawe
VERSION = 'OutputFormatterModule 1.0.0'

def format_write_summary_csv( summary_csv, datetimeStamp, output_dir ):
	# first import column mappings from file
	import column_renames as cr
	col_maps = cr.column_renames
	
	# second read the csv into a pandas dataframe
	df = pd.read_csv( summary_csv, sep=',' )
	if not len(df.columns) == len(col_maps):
		print 'ERROR: Unequal number of column renames! Read in from _summary: ' + str(len(df.columns)) + ' Found in rename file: ' + str(len(col_maps))
		raise(dawe.OutputFormatterError(1904))
	
	# third add column 'Analysis Time' for datetime
	df['AnalysisTime'] = datetimeStamp
	
	# fourth loop over column name remapping
	try:
		for key, value in col_maps.iteritems():
			df.rename(columns={key:value}, inplace=True)
	except:
		raise(dawe.OutputFormatterError(1903))
		
	mutation = df['Mutation']
	mutation.replace('', np.nan, inplace=True)
	df['Mutation'] = mutation
	
	# drop rows where Mutation is NaN
	df = df[pd.notnull(df['Mutation'])]
	df = df[df['Mutation'] != 'WT']
	df = df[df['Mutation'] != 'NA']
	
	# clean up any blanks to NaN
	#def cleanBlanks(row):
	#	for column in row:
	#		row[column].replace('', np.nan, inplace=True)
	#	return row
	#df = df.apply(cleanBlanks)
	
	# fifth loop over rows to remove fits, GEq, and Detects for ANY row that fails QC
	for index, row in df.iterrows():
		if row['Count_QC'] == 'FAIL':
			df.loc[ index, "p_fit" ] = ''
			df.loc[ index, "p_lower" ] = ''
			df.loc[ index, "p_upper" ] = ''
			df.loc[ index, "p_call" ] = ''
			df.loc[ index, "GEq" ] = ''
			df.loc[ index, "GEq_lower" ] = ''
			df.loc[ index, "GEq_upper" ] = ''
		if df.loc[ index, "adj_mutant_reads" ] < 0:
			df.loc[ index, "adj_mutant_reads" ] = 0
	
	# finally write out new dataframe to csv file
	new_filename = os.path.splitext(os.path.basename( summary_csv ))[0]
	new_filename = new_filename.split('_summary')[ 0 ]
	new_filename = new_filename + "_" + datetimeStamp + "_summary.csv"
	new_filename = os.path.join( output_dir, new_filename )
	try:
		df.to_csv(new_filename, sep=',', index=False, quoting=csv.QUOTE_ALL)
	except:
		raise
	
	#print "\t" + "Formatting and copying final _summary complete! See: " + new_filename
	
def copy_stats_csv( stats_csv, datetimeStamp, output_dir ):
	## quote all columns
	
	# read the csv into a pandas dataframe
	df = pd.read_csv( stats_csv, sep=',' )
	# remove any 'NA' strings
	#df - df.apply(cleanBlanks)
	
	# uppercase Assay column
	df['Assay'] = map(lambda x: str(x).upper(), df['Assay'])
	
	# convert Metrics column from string to float [trim off +/- etc]
	try:
		for i, row in df.iterrows():
			value = str(row['Metric']).lstrip().split(' ')[0]
			df.loc[i, 'Metric'] = value
	except:
		raise(dawe.OutputFormatterError(1902))
	
	# set up new filename
	new_filename = os.path.splitext(os.path.basename( stats_csv ))[0]
	new_filename = new_filename.split('_stats')[ 0 ]
	new_filename = new_filename + "_" + datetimeStamp + "_stats.csv"
	new_filename = os.path.join( output_dir, new_filename )
	# write file to output
	try:
		#shutil.copyfile( stats_csv , new_filename )
		df.to_csv(new_filename, sep=',', index=False, quoting=csv.QUOTE_ALL)
	except Exception as err:
		raise

def copy_rawcounts_csv( rawcounts_csv, datetimeStamp, output_dir ):
	# set up new filename
	new_filename = os.path.splitext(os.path.basename( rawcounts_csv ))[0]
	new_filename = new_filename.split('_RAWCOUNTS')[ 0 ]
	new_filename = new_filename + "_" + datetimeStamp + "_RAWCOUNTS.csv"
	new_filename = os.path.join( output_dir, new_filename )
	# copy file to output
	try:
		shutil.copyfile( rawcounts_csv , new_filename )
	except Exception as err:
		raise
		
def copy_samplesheet_csv( samplesheet, datetimeStamp, output_dir ):
	# set up new filename
	new_filename = os.path.splitext(os.path.basename( samplesheet ))[0]
	new_filename = new_filename.split('_SampleSheet_Used')[ 0 ]
	new_filename = new_filename + "_" + datetimeStamp + "_SampleSheet_Used.csv"
	new_filename = os.path.join( output_dir, new_filename )
	# copy file to output
	try:
		shutil.copyfile( samplesheet , new_filename )
	except Exception as err:
		raise

def copy_plots_pdf( plots_pdf, datetimeStamp, output_dir ):
	# set up new filename
	new_filename = os.path.splitext(os.path.basename( plots_pdf ))[0]
	new_filename = new_filename.split('_all_plots')[ 0 ]
	new_filename = new_filename + "_" + datetimeStamp + "_all_plots.pdf"
	new_filename = os.path.join( output_dir, new_filename )
	# copy file to output
	try:
		shutil.copyfile( plots_pdf , new_filename )
	except Exception as err:
		raise

def runOutputFormatter( samplesheet, stats, rawcounts, pdf, summary, output_dir, runid ):
	try:
		print 'Output Formatter module version is " ' + VERSION + ' "\n'

		print "\tSAMPLESHEET FILE: " + samplesheet
		print "\tSTATS FILE: " + stats
		print "\tRAWCOUNTS FILE: " + rawcounts
		print "\tPLOTS PDF FILE: " + pdf
		print "\tUNFORMATTED SUMMARY FILE: " + summary
		print "\tOUTPUT DIR: " + output_dir
		print "\tRUNID: " + runid	
		print
		
		# generate datetimeStamp
		#stamp = time.strftime('%H%M%S_%m%d%Y')
		#stamp = time.strftime('%m%d%Y_%H%M%S')
		stamp = time.strftime('%Y%m%d_%H%M%S')
		
		# set output_dir
		output_dir = os.path.join( output_dir, runid )
		if not os.path.exists( output_dir ):
			os.makedirs( output_dir )
		
		# first we copy the sample sheet
		if (samplesheet != '' and os.path.exists( samplesheet )):
			copy_samplesheet_csv( samplesheet, stamp, output_dir )
			
		# second lets copy the stats file
		if stats != '' and os.path.exists( stats ):
			copy_stats_csv( stats, stamp, output_dir )
		
		# then only if summary is empty, copy rawcounts
		if (rawcounts != '' and os.path.exists ( rawcounts ) and summary == ''):
			print "WARNING: Output from DataAnalysis module not found! Copying _RAWCOUNTS file " + rawcounts + " to output directory instead..."
			copy_rawcounts_csv( rawcounts, stamp, output_dir )
		elif (summary != '' and os.path.exists ( summary )):
			#print "Output from DataAnalysis module found! Copying _summary file " + summary + " to output directory..."
			format_write_summary_csv( summary, stamp, output_dir )
		
		# finally copy pdf
		if (pdf != '' and os.path.exists ( pdf )):
			#print "Plots from DataAnalysis module found! Copying _all_plots file " + pdf + " to output directory..."
			copy_plots_pdf( pdf, stamp, output_dir )
		
		print "\tCopying files complete! See: " + output_dir + " for final output"
		print
		
		return 0
		
	except (dawe.UnknownOSError, dawe.OptionError, dawe.PathError, dawe.SSValidatorError, dawe.PipelineError, dawe.ConfigFileError, dawe.SequencingQcError, dawe.ReadsProcessingError, dawe.DataAnalysisError, dawe.OutputFormatterError) as err:
		print "Error %d: %s" % (err.args[0], err.em[err.args[0]])
		print
		
		return err.args[0]
		
	except:
		print 'Unexpected error:',sys.exc_info()[0]
		print 'Traceback:',sys.exc_info()[2], traceback.format_exc()
		print
		
		return 1

	
	
def cleanBlanks(row):
	for column in row:
		print 'COLUMN: ' + column + ' ROW: ' + row
	return row

# for use as a script
if __name__ == "__main__":
	if len(sys.argv) < 7:
		print "USAGE: python " + str(sys.argv[0]) + " samplesheet stats rawcounts pdf summary output_dir runId"
		sys.exit(0)
	else:
		#if os.path.exists( os.path.join( sys.argv[6], sys.argv[7] ) ):
			#shutil.rmtree(os.path.join( sys.argv[6], sys.argv[7] ))
		if not os.path.exists( os.path.join( sys.argv[6], sys.argv[7] ) ):
			os.makedirs( os.path.join( sys.argv[6], sys.argv[7] ) )
		
		retcode = runOutputFormatter( sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7] )
		print "RETURN CODE: " + str(retcode)









