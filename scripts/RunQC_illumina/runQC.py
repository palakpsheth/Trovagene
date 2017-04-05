#!/usr/bin/env python
from __future__ import division
import sys
import glob
import os
import operator
import time
import subprocess
from StringIO import StringIO
import pandas as pd
import re
from configobj import ConfigObj
import inspect
import matplotlib.pyplot as plt
import numpy as np

VERSION = 'RunQCReporter 1.1.0'

# this module runs the Illumina InterOp parser and generates a sequencing QC stats file
def check_run( basecalls_dir, working_dir, toolVersion, sampleSheet, configFile ) :
	
	print 'Sequencing QC module version is " ' + VERSION + ' "\n'
	msg = ''
	
	# define location of Illumina InterOp parser bin
	BINPATH = os.path.abspath( os.path.join( 'scripts', 'RunQC_illumina', 'interop_linux_gcc46_release', 'bin'))
	if not os.path.exists( BINPATH ):
		BINPATH = os.path.abspath( os.path.join( os.path.dirname(__file__), 'interop_linux_gcc46_release', 'bin'))
	
	# verify that analysis is complete
	is_complete, step, cpFile = VerifyPrimaryAnalysisComplete( basecalls_dir )
	if not is_complete:
		msg = 'ERROR: Primary analysis complete flag not found in file: ' + str(cpFile) + '  Last step: ' + str(step)
		return False, msg
	
	# make sure InterOp folder exists
	baseRunFolder = basecalls_dir.split('/Data/Intensities/BaseCalls')[ 0 ]
	runID = os.path.basename( baseRunFolder )
	INTEROP = os.path.join( baseRunFolder, 'InterOp' )
	#print 'INTEROP: ' + INTEROP
	if not os.path.exists( INTEROP ):
		msg = 'ERROR: InterOp folder ' + INTEROP + ' not found!\n'
		print msg
		return False, msg
	
	# clean up any old stats files
	if os.path.exists ( os.path.join( working_dir , runID, runID + "_stats.csv" ) ) :
		os.remove( os.path.join( working_dir , runID, runID + "_stats.csv" ) )
		
	
	# get summary info as CSV
	SUMMARY = os.path.join( BINPATH, 'summary' )
	#print 'SUMMARY: ' + SUMMARY
	output=''
	if os.path.exists( SUMMARY ):
		cmd = SUMMARY + ' ' + baseRunFolder
		print '\tRunning command: ' + cmd 
		try:
			output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, universal_newlines=True, shell=True)
		except subprocess.CalledProcessError as err:
			msg = 'ERROR: ' + str(err) + "\n" + err.output + "\n"
			print msg
			return False, msg
	else:
		msg = 'ERROR: Run QC binary file ' + SUMMARY + ' not found!\n'
		print msg
		return False, msg
	
	# write summary data report from summary CSV
	write_summary_report( output, working_dir, toolVersion, runID, basecalls_dir )
	
	# get indexing info as CSV
	INDEX = os.path.join( BINPATH, 'interop2csv' )
	#print 'SUMMARY: ' + SUMMARY
	output=''
	indexBin = os.path.join( INTEROP, 'IndexMetricsOut.bin' )
	print indexBin
	if os.path.exists( INDEX ) and os.path.exists( indexBin ):
		cmd = INDEX + ' ' + indexBin
		print '\tRunning command: ' + cmd 
		try:
			output = subprocess.check_output(cmd, stderr=(open(os.devnull, 'w')), universal_newlines=True, shell=True)
		except subprocess.CalledProcessError as err:
			msg = 'ERROR: ' + str(err) + "\n" + err.output + "\n"
			print msg
			return False, msg
	elif not os.path.exists( INDEX ):
		msg = 'ERROR: Run QC binary file ' + INDEX + ' not found!\n'
		print msg
		return False, msg
	elif not os.path.exists( indexBin ):
		msg = 'ERROR: InterOp folder binary file ' + indexBin + ' not found!\n'
		print msg
		return False, msg
	
	# write standard group / type specific info
	append_sample_report( output, sampleSheet, working_dir, toolVersion, runID )
	
	# if output stats file exists, continue
	statsFile = os.path.join( working_dir, runID, runID + '_stats.csv' )
	if os.path.exists( statsFile ):
		is_ok, msg = evaluateQCmetrics( statsFile, configFile )
		#is_ok = True
	else:
		msg = 'ERROR: _stats.csv file not found at: ' + statsFile + '\n'
		return False, msg
	
	# generate graph of clusters distribution
	graphClsutersDistribution( statsFile, working_dir, runID )
	
	print
	# return results
	return is_ok, msg
	
	
	
	
	
	
	
	
	
	
	
	

def write_summary_report( data, working_dir, toolVersion, runID, basecalls_dir ) :
	
	# remove any comments and clean up blank spaces
	data = re.sub("^#.*\n",'', data.rstrip())
	data = re.sub("\s\s*,",',', data.rstrip())
	data = re.sub("\s\s*\n",'\n', data.rstrip())
	
	# summary csv is in two section so split
	splitData = data.split('Read 1\n')
	
	# load each section into dataframes
	dataTop = StringIO(splitData[0])
	dfTop = pd.read_csv(dataTop, sep=',')
	dataBot = StringIO(splitData[1])
	dfBot = pd.read_csv(dataBot, sep=',')
	
	#print dfTop.columns
	#print_full(dfTop)
	#print
	#print dfBot.columns
	#print
	
	# open output file for printing and print header
	#print 'Working dir: ' + working_dir
	#print 'RunID: ' + runID
	if not os.path.exists( os.path.join( working_dir , runID ) ):
		os.makedirs( os.path.join( working_dir , runID ) )
	file = open( os.path.join( working_dir , runID, runID + "_stats.csv" ) , 'wb' )
	#print os.path.join( working_dir , runID, runID + "_stats.csv" )
	file.write( "RunId,Tool,FLAG,Assay,Input,Source,StandardGroup,Type,Metric,Comments,Status\n" )

	## print stuff from top half
	# print yield info
	file.write( runID + 
				"," + toolVersion +
				"," + 'Yield' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(dfTop['Yield'][0]) +
				"," + 'Read 1 yield in gigabases (G)' + '\n')
	
	# print %>=Q30 info
	file.write( runID + 
				"," + toolVersion +
				"," + 'Percent Bases >=Q30' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(dfTop['%>=Q30'][0]) +
				"," + 'Read 1 percent bases >= Q30' + '\n' )
				
	# print aligned phix info
	file.write( runID + 
				"," + toolVersion +
				"," + 'Percent PhiX Aligned' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				#"," + str(dfTop['Aligned'][0]) +
				"," + str(dfBot['Aligned'][0]) +
				"," + 'Read 1 percent PhiX aligned should be >= 5.00' + '\n')
				
	# print phix error rate info
	file.write( runID + 
				"," + toolVersion +
				"," + 'PhiX Control Error Rate' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				#"," + str(dfTop['Error Rate'][0]) +
				"," + str(dfBot['Error'][0]) +
				"," + 'Read 1 PhiX error rate should be <= 0.50' + '\n' )
				
	## print stuff from bottom half
	# print cluster density info
	file.write( runID + 
				"," + toolVersion +
				"," + 'Raw Cluster Density' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(dfBot['Density'][0]) +
				"," + 'Read 1 raw cluster density (K/mm^2) should be >= 500K/mm^2 and <= 1200K/mm^2' + '\n' )
				
	# print clusters PF info
	file.write( runID + 
				"," + toolVersion +
				"," + 'Percent Clusters PF' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(dfBot['Cluster PF'][0]) +
				"," + 'Read 1 percentage of clusters passing filter should be >= 75' + '\n' )
				
	# print phasing/prephasing info
	value = str(dfBot['Phas/Prephas'][0])
	phasing = str(value.split("/")[ 0 ]).strip()
	prephasing = str(value.split("/")[ 1 ]).strip()
	file.write( runID + 
				"," + toolVersion +
				"," + 'Phasing' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + phasing +
				"," + 'Read 1 phasing applied should be <= 0.50' + '\n' )
	file.write( runID + 
				"," + toolVersion +
				"," + 'Prephasing' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + prephasing +
				"," + 'Read 1 prephasing applied should be <= 0.30' + '\n' )
				
	## print custom calculated stuff
	# Average percent clusters failed demux
	avgFailedDemux = CalculatePercentFailedDemux( basecalls_dir )
	file.write( runID + 
				"," + toolVersion +
				"," + 'Percent Clusters Failed Demux' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(avgFailedDemux) +
				"," + 'Average percentage of clusters (across all tiles) assigned to \'Undetermined\' should be <= 20' + '\n' )
	# Average percent tiles failed demux
	avgFailedDemux = CalculatePercentTileDemuxFail( basecalls_dir )
	file.write( runID + 
				"," + toolVersion +
				"," + 'Percent Tiles Failed Demux' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(avgFailedDemux) +
				"," + 'Percentage of tiles without all samples present should be <= 10' + '\n' )
				
	file.close()

def append_sample_report( data, sampleSheet, working_dir, toolVersion, runID ) :
	data = data.split("\n")
	
	# load index data into dataframe
	indexData = loadIndexDataFrame( data )
	
	# load sampleSheet into dataframe
	sampleSheetData = loadSampleSheetDataFrame( sampleSheet )
	
	# merge dataframes
	#print indexData.columns
	#print sampleSheetData.columns
	mergedDf = pd.merge(sampleSheetData, indexData, on='Index')
	#print mergedDf
	#print
	
	# open output file for printing and print header
	if not os.path.exists( os.path.join( working_dir , runID ) ):
		os.makedirs( os.path.join( working_dir , runID ) )
	file = open( os.path.join( working_dir , runID, runID + "_stats.csv" ) , 'ab' )
	
	## loop thru mergedDf to print grouping stats
	
	# get and print total clustersPF
	totalClustersPF = mergedDf['ClustersPF'].sum()
	file.write( runID + 
				"," + toolVersion +
				"," + 'Total Clusters PF' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + 'ALL' +
				"," + str(totalClustersPF) +
				"," + 'Total number of clusters passing Illumina chastity filter (PF)' + '\n' )
	
	# group by standard group then by description
	stdGrpNames = mergedDf['Standard_Group'].unique()
	typeNames = mergedDf['Description'].unique()
	
	for stdGrpName in stdGrpNames :
		# for this standard group, figure out percentage of clustersPF
		groupSum = mergedDf.loc[mergedDf['Standard_Group'] == stdGrpName]['ClustersPF'].sum()
		assay = mergedDf.loc[mergedDf['Standard_Group'] == stdGrpName]['Sample_Project'].unique()[ 0 ]
		inp = mergedDf.loc[mergedDf['Standard_Group'] == stdGrpName]['Input'].unique()[ 0 ]
		source = mergedDf.loc[mergedDf['Standard_Group'] == stdGrpName]['Source'].unique()[ 0 ]
		#print groupSum
		percentage = int(groupSum) / totalClustersPF * 100
		file.write( runID + 
					"," + toolVersion +
					"," + 'Percent Clusters Per Standard Group' +
					"," + str(assay).upper() +
					"," + str(inp) + 
					"," + str(source) +
					"," + str(stdGrpName) +
					"," + 'ALL' +
					"," + str(percentage) +
					"," + 'Percentage of total clusters PF assigned to Standard Group: ' + str(stdGrpName) + '\n' )
		for typeName in typeNames :
			# for this standard group, type combo figure out percentage of clustersPF
			typeList = mergedDf.loc[(mergedDf['Standard_Group'] == stdGrpName) & (mergedDf['Description'] == typeName)]['ClustersPF']
			if len(typeList)>0:
				typeSum = mergedDf.loc[(mergedDf['Standard_Group'] == stdGrpName) & (mergedDf['Description'] == typeName)]['ClustersPF'].sum()
				#print
				#print typeSum
				#print
				percentage = int(typeSum) / int(groupSum) * 100
				file.write( runID + 
							"," + toolVersion +
							"," + 'Percent Clusters Per Type per Standard Group' +
							"," + str(assay).upper() +
							"," + str(inp) + 
							"," + str(source) +
							"," + str(stdGrpName) +
							"," + str(typeName) +
							"," + str(percentage) +
							"," + 'Percentage of clusters PF within Standard Group: ' + str(stdGrpName) + ' assigned to Type: '+ str(typeName) + '\n' )






	
def print_full(x):
    pd.set_option('display.max_rows', len(x))
    print(x)
    pd.reset_option('display.max_rows')

# Checks that the instrument completed demux & fastq file generation
def VerifyPrimaryAnalysisComplete( basecalls_dir ) :
	#illumina_alignment_dir = fileUtils.AlignmentDirectoryFromBaseCalls( config.basecalls_dir )
	checkpoint_files = glob.glob( os.path.join( basecalls_dir, "Alignment*", "Checkpoint.txt" ) )
	if len(checkpoint_files) > 0:
		checkpoint_file = get_youngest_file( checkpoint_files )
		step = 'NA'
	if os.path.exists( checkpoint_file ) :
		cpFile = os.path.realpath( checkpoint_file )
		f = open( checkpoint_file , 'rb')
		line = f.readline().strip()
		f.close()
			
		step = int( line )
			
		if step >= 3 : 
			return True, step, cpFile
		else :
			return False, step, cpFile
	else :
		return False, step, cpFile

# calculates average percent failure amongst all tiles
def CalculatePercentFailedDemux( basecalls_dir ) :
	#alignmentDirs = glob.glob( os.path.join( basecalls_dir, "Alignment*", "DemultiplexSummaryF1L1.txt" ) )
	alignmentDir = AlignmentDirectoryFromBaseCalls( basecalls_dir )
	demux_report = glob.glob( os.path.join( alignmentDir, "DemultiplexSummaryF1L1.txt" ) )
	if len(demux_report) > 0:
		demux_report = demux_report[0]	
		if os.path.exists( demux_report ):
			percent_failed = list()
			foundHeader = False
			finished    = False
			
			for line in open( demux_report , 'rb' ) :
				if not foundHeader :
					if line.strip().startswith("SampleName") :
						foundHeader = True
						continue
					else : continue
				if foundHeader and not finished :
					tokens = line.strip().split('\t')
					if len( tokens ) > 2 :
						percent_failed.append( float( tokens[1] ) )
					else : finished = True
				
			if len( percent_failed ) != 0 :
				average_percent_failed = reduce( lambda x, y: x + y, percent_failed ) / len( percent_failed )
			else : average_percent_failed = 0
				
			return average_percent_failed
		else : average_percent_failed = 'NA'
	else : average_percent_failed = 'NA'
	
	return average_percent_failed
			
def CalculatePercentTileDemuxFail( basecalls_dir ) :
	alignmentDir = AlignmentDirectoryFromBaseCalls( basecalls_dir )
	demux_report = glob.glob( os.path.join( alignmentDir, "DemultiplexSummaryF1L1.txt" ) )
	if len(demux_report)>0:
		demux_report = demux_report[ 0 ]
	else:
		raise Exception('ERROR: DemultiplexSummaryF1L1.txt file not found in Alignment directory ' + str(alignmentDir))
	if os.path.exists( demux_report ):		
		zero_tiles  = 0
		total_tiles = 0	
		foundHeader = False
		finished    = False
		
		for line in open( demux_report , 'rb' ) :
			if not foundHeader :
				if line.strip().startswith("SampleName") :
					foundHeader = True
					continue
				else : continue
			if foundHeader and not finished :
				tokens = line.strip().split('\t')
				if len( tokens ) > 2 :
					column_count = 0
					for token in tokens :
						if column_count > 1 :
							if float( token ) <= 0 :
								zero_tiles += 1
							total_tiles += 1
						column_count += 1
				else : finished = True

		if total_tiles > 0 :
			#print 'Demux file: ' + demux_report
			#print 'Total tiles: ' + str(total_tiles)
			#print 'Zero tiles: ' + str(zero_tiles)
			average_percent_failed = ( zero_tiles / total_tiles ) * 100
			#print average_percent_failed
		else : average_percent_failed = 100
			
		return average_percent_failed
		
def AlignmentDirectoryFromBaseCalls( basecalls_dir ) :
	alignment_directories = glob.glob( os.path.join( basecalls_dir , "Alignment*" ) )
	if len( alignment_directories ) > 0 : 
		return sorted( alignment_directories , reverse=True )[0]
	else : 
		return ""
	
def loadSampleSheetDataFrame( sampleSheet ) :
	with open(sampleSheet) as f:
		sheet = f.readlines()
		
	data = ''
	go = False
	for index, line in enumerate(sheet):
		#line = line.strip()
		if not go:
			if line.startswith('[Data]'):
				dataIndex = index
				go = True
		elif go:
			#data.append(line)
			data = data + line
	
	data = StringIO(data)
	df = pd.read_csv(data, sep=',')
	colNames = list(df.columns.values)
	if 'index' in colNames:
		df.rename(columns={'index':'Index'}, inplace=True)
	
	return df
	
def loadIndexDataFrame( data ) :
	# delete the header lines
	cleanData = []
	for line in data:
		if not line.startswith('#'):
			cleanData.append(line)
	
	# load index data into dataframe
	cleanData = '\n'.join(cleanData)
	
	indexData = pd.read_csv((StringIO(cleanData)), sep=',')
	# fix header names so they can be merged
	indexData=indexData.rename(columns = {'Sample':'Sample_ID'})
	indexData=indexData.rename(columns = {'Sequence':'Index'})
	
	# summarize data
	correctedSequence = indexData['Index'].replace('-','',regex=True)
	indexData['Index'] = correctedSequence
	summaryDf1 = indexData.groupby(by=['Index'])['Count'].sum().to_frame( name='ClustersPF' )
	summaryDf1.index.name = 'Index'
	summaryDf1.reset_index(inplace=True)

	#summaryDf2 = indexData.groupby(by=['Index'])['Count'].mean().to_frame( name='Mean' )
	#summaryDf2.index.name = 'Index'
	#summaryDf2.reset_index(inplace=True)
	#summaryDf = pd.merge(summaryDf1, summaryDf2)

	#summaryDf3 = indexData.groupby(by=['Index'])['Count'].median().to_frame( name='Median' )
	#summaryDf3.index.name = 'Index'
	#summaryDf3.reset_index(inplace=True)
	#summaryDf = pd.merge(summaryDf, summaryDf3)
	
	#summaryDf4 = indexData.groupby(by=['Index'])['Count'].std().to_frame( name='StdDev' )
	#summaryDf4.index.name = 'Index'
	#summaryDf4.reset_index(inplace=True)
	#summaryDf = pd.merge(summaryDf, summaryDf4)

	#print summaryDf
	
	return summaryDf1
	
def evaluateQCmetrics( statsFile, configFile ):
	is_ok = True
	msg = ''
	
	# read file into dataframe
	df = pd.read_csv(statsFile, sep=',')
	
	#read config file and get thresholds
	Config = ConfigObj(configFile, raise_errors=True)
	thresholds = Config['runQC']
	
	# set thresholds
	##### ADD OTHER VALUES HERE #####
	#thresholds = {'Percent Clusters Failed Demux':20}
	
	# loop thru thresholds and check dataframe if failing
	for key, value in thresholds.iteritems():
		#print 'KEY: ' + key + '\n'
		found = df.loc[df['FLAG'] == key]['Metric'].tolist()[ 0 ]
		if not found == 'NA': 
			if "Failed" in key:
				if float(found) > float(value):
					is_ok = False
					msg = msg + key + ' not in spec. Should be <= ' + str(value) + ' but found: ' + str(found) + '\n'
					df.ix[df.FLAG == key, 'Status'] = "FAIL"
				else:
					df.ix[df.FLAG == key, 'Status'] = "PASS"
			else:
				if float(found) < float(value):
					is_ok = False
					msg = msg + key + ' not in spec. Should be >= ' + str(value) + ' but found: ' + str(found) + '\n'
					df.ix[df.FLAG == key, 'Status'] = "FAIL"
				else:
					df.ix[df.FLAG == key, 'Status'] = "PASS"
	
	#write out new csv
	df.to_csv(statsFile, sep=',', index=False)
				
	#return results
	return is_ok, msg

def get_oldest_file(files, _invert=False):
    """ Find and return the oldest file of input file names.
    Only one wins tie. Values based on time distance from present.
    Use of `_invert` inverts logic to make this a youngest routine,
    to be used more clearly via `get_youngest_file`.
    """
    gt = operator.lt if _invert else operator.gt
    # Check for empty list.
    if not files:
        return None
    # Raw epoch distance.
    now = time.time()
    # Select first as arbitrary sentinel file, storing name and age.
    oldest = files[0], now - os.path.getctime(files[0])
    # Iterate over all remaining files.
    for f in files[1:]:
        age = now - os.path.getctime(f)
        if gt(age, oldest[1]):
            # Set new oldest.
            oldest = f, age
    # Return just the name of oldest file.
    return oldest[0]

def get_youngest_file(files):
    return get_oldest_file(files, _invert=True)
    
def graphClsutersDistribution( statsFile, working_dir, runID ):
	# read in stats file
	with open(statsFile) as f:
		stats = f.readlines()
		
	data = ''
	for index, line in enumerate(stats):
		#line = line.strip()
		if line.startswith('RunId'): # Header
			data = data + line
		elif 'Percent Clusters Per' in line:
			data = data + line
	
	#print
	#print data
	data = StringIO(data)
	#df = pd.read_csv(data, sep=',')
