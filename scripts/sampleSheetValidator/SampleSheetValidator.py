#!/usr/bin/env python
from __future__ import division
import sys, os
sys.path.append('../../../../')
import getopt
import datetime
import inspect
import re
import pandas as pd
import numpy as np
import time
from subprocess import call

# import custom modules
import DataAnalysisWrapperErrors as dawe

VERSION = 'SampleSheetValidator 1.1.0'

def main(argv):
	try:
		# installation params and defaults
		ssv_path = inspect.getsourcefile(lambda:0)
		ssv_ver = os.path.basename(ssv_path)

		options = parse_options(argv, ssv_ver)

		sampledata, samplesheet, files, assaydata, assayDf, sampleheader = validate_sample_sheet(options['sample_sheet'], options['basecalls_dir'], options['csv_cache'], options['ss_infer_info'])

		return 0

	except (dawe.UnknownOSError, dawe.OptionError, dawe.PathError, dawe.SSValidatorError, dawe.PipelineError) as err:
		print "Error %d: %s" % (err.args[0], err.em[err.args[0]])

		return err.args[0]

	except:
		print 'Unexpected error:',sys.exc_info()[0]
		
		return 1

def parse_options(argv, ssv_ver):
	options = {}
	options['basecalls_dir'] = ''
	options['csv_cache'] = ''
	options['sample_sheet'] = ''
	options['ss_infer_info'] = 1		# default to not infer info -- to make backwards compatible, this should be enabled

	try:
		opts, remainder = getopt.getopt(argv,   "hi:c:s:n:",
											[   "help",
												"basecalls_dir=",
												"csv_cache=",
												"sample_sheet=",
												"ss_infer_info="])
	except getopt.GetoptError as err:
		# show MWE for usage
		print 'ERROR:',str(err)
		print 'Sample sheet validator call with minimal arguments:'
		print 'TODO'
	# parse opts
	for opt, arg in opts:
		if opt in ('-h', "--help"):
			print 'Sample sheet validator call with minimal arguments:'
			print 'TODO'
		elif opt in ("-i", "--basecalls_dir"):
			options['basecalls_dir'] = arg
		elif opt in ("-c", "--csv_cache"):
			options['csv_cache'] = arg
		elif opt in ("-s", "--sample_sheet"):
			options['sample_sheet'] = arg
		elif opt in ("-n", "--ss_infer_info"):
			options['ss_infer_info'] = arg
	# enforce minimal requirement
	# NOTE: either need basecalls_dir or csv_cache (sample_sheet may be inferred from basecalls_dir or separately specified)
	if ((options['basecalls_dir'] == '' and options['csv_cache'] == '') or options['sample_sheet'] == ''):
		# show MWE for usage
		print 'Sample sheet validator call with minimal arguments:'
		print 'TODO'
	if not os.path.exists(options['basecalls_dir']):
		raise dawe.PathError(1202)
	if not os.path.exists(options['sample_sheet']):
		raise dawe.PathError(1212)

	return options

def validate_sample_sheet(sample_sheet, ss_infer_info, basecalls_dir=None ):
	print '\tValidating SampleSheet...'
	print
	
	# suppresses warning about potentially confusing 'chained assignments' (but generates false positives for sampledata['Sample_ID'] = sampledata['Sample_ID'].astype(int) )
	pd.options.mode.chained_assignment = None  # default='warn'

	#print 'Reading sample sheet'
	samplesheet = pd.read_csv(sample_sheet, header=None)		# problem: can't infer column types when loading like this
																# solution: cast columns as specified types? -- must be done after parsing headers after finding [Data]
																# solution 2: reload after determining where data starts, and set header when reading in
																# e.g. samplesheet = pd.read_csv(sample_sheet, header=data_row)
	#samplesheet = pd.DataFrame.from_csv(sample_sheet, header=None, index_col=None)

	# getSampleHeader
	data_rows = samplesheet[samplesheet[0] == '[Data]'].index.tolist()
	if (len(data_rows) > 1):
		raise dawe.SSValidatorError(1301)
	elif (len(data_rows) == 0):
		raise dawe.SSValidatorError(1302)
	else:
		data_row = data_rows[0]
		#print 'Data begins after row:',data_row
	sampleheader = samplesheet.iloc[:(data_row+1),:]
	data_headers = samplesheet.iloc[data_row+1,:].tolist()

	# getSampleData
	sampledata = samplesheet.iloc[(data_row+2):,:]
	# remove blank rows
	sampledata = sampledata.dropna(how='all', axis=0)

	###############################################################
	# this is where it gets complicated...
	# need to validate each column, grouping etc BUT two diff modes: ss_infer_info[0] or [1]
	# if ss_infer_info[1], try to infer or fix information. 
	# if ss_infer_info[0], validate the entry but then error out
	###############################################################
	
	# fix headers
	if (int(ss_infer_info) == 1):
		data_headers = checkSSNames(data_headers)
		sampledata.columns = data_headers
	else:
		# remove blank entries
		data_headers = filter(None, data_headers)
		sampledata.columns = data_headers
	#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,Index,Sample_Project,Description,Ng_Per_Rxn,Source,Standard_Group,PhiX_Fraction,Batch,Checkout_Number,Input,Project_Version

	##### FIRST ADDRESS MINIMAL REQUIRED COLUMNS #####

	# Sample_ID column
	if 'Sample_ID' in data_headers:
		# check column type
		try:
			sampledata['Sample_ID'] = sampledata['Sample_ID'].astype(int)
		except:
			raise dawe.SSValidatorError(1319)
		
		# check Sample_ID
		# need to do this for all SampleSheets regardless of ss_infer_info??? - NO
		if (int(ss_infer_info) == 1):
			if (len(sampledata['Sample_ID']) == sampledata['Sample_ID'].max()):
				print '\tSample Number Matching ID Length, Still Assigning Sequential ID'
			else:
				# Sample_ID is missing one or more numbers from integer sequence
				print '\tWARNING: Sample ID Numbering Issue Found..., Assigning Sequential ID'
			sampledata['Sample_ID'] = map(lambda x:x+1, list(range(len(sampledata['Sample_ID']))) )		# could also use list comprehensions
		else:
			if not (len(sampledata['Sample_ID']) == sampledata['Sample_ID'].max()) or not (sampledata['Sample_ID'].min() == 1) :
				raise dawe.SSValidatorError(1321)
			else:
				print '\tSample Number Matching ID Length'
	else:
		raise dawe.SSValidatorError(1303)
	
	# Sample_Name column
	if 'Sample_Name' in data_headers:
		# check column type
		try:
			sampledata['Sample_Name'] = sampledata['Sample_Name'].astype(str)
		except:
			raise dawe.SSValidatorError(1320)
			
		# check Sample_Name
		# need to do this for all SampleSheets regardless of ss_infer_info??? - NO
		if (int(ss_infer_info) == 1):
			# checkSampleName -- do Sample_Name conversion based on Illumina protocol
			sname = sampledata['Sample_Name']
			sname = [re.sub('[^a-zA-Z0-9]', '-', elem, flags=re.IGNORECASE) for elem in sname]		# any non-alphanumeric char (including hyphen) to hyphen
			sname = [re.sub('-+', '-', elem, flags=re.IGNORECASE) for elem in sname]				# multiple hyphens to one hyphen
			sname = [re.sub('-$', '', elem, flags=re.IGNORECASE) for elem in sname]					# trailing hyphen
			sampledata['Sample_Name'] = sname
			print '\tSample names have been cleaned of all non-alphanumeric characters'
		else:
			sname = sampledata['Sample_Name']
			for elem in sname:
				if re.search('[^a-zA-Z0-9\-]', elem, flags=re.IGNORECASE) is not None:
					raise dawe.SSValidatorError(1322)
	else:
		dawe.SSValidatorError(1304)
		
	# Sample_Plate column
	if not 'Sample_Plate' in data_headers:
		raise dawe.SSValidatorError(1323)
	
	# Sample_Well column
	if not 'Sample_Well' in data_headers:
		raise dawe.SSValidatorError(1324)
		
	# I7_Index_ID column
	if not 'I7_Index_ID' in data_headers:
		raise dawe.SSValidatorError(1327)
	
	# Index column
	if 'Index' in data_headers:
		# check column type
		try:
			sampledata['Index'] = sampledata['Index'].astype(str)
		except:
			raise dawe.SSValidatorError(1329)	
	elif 'index' in data_headers:
		# check column type
		try:
			sampledata['index'] = sampledata['index'].astype(str)
		except:
			raise dawe.SSValidatorError(1329)	
	else:
		raise dawe.SSValidatorError(1328)
	
	# Sample_Project column
	if 'Sample_Project' in data_headers:
		# check column type
		try:
			sampledata['Sample_Project'] = sampledata['Sample_Project'].astype(str)
		except:
			raise dawe.SSValidatorError(1330)
			
		# check Sample_Project
		assay = sampledata['Sample_Project']
		assay.replace('', np.nan, inplace=True)
		assay.dropna(inplace=True)
		if (int(ss_infer_info) == 1):
			assay = checkAssayType(assay)
			sampledata['Sample_Project'] = assay
			print '\t"Sample_Project" column containing assay names has been unified'
		else:
			for elem in assay:
				if not re.search('EGFR_L858R|EGFR_T790M|EGFR_Ex19del|EGFR_Ex19Del|EGFR_EX19DEL|BRAF_V600X|KRAS_G12X', elem, flags=re.IGNORECASE):
					raise dawe.SSValidatorError(1331)		
	else:
		raise dawe.SSValidatorError(1305)
	
	# Description column
	if 'Description' in data_headers:
		sType = sampledata['Description']
		sType.replace('', np.nan, inplace=True)
		sType.dropna(inplace=True)		
		# check column type
		try:
			sampledata['Description'] = sampledata['Description'].astype(str)
		except:
			if (int(ss_infer_info) == 1):
				# default is "Sample"
				sampledata['Description'] = ['Sample'] * len(sids)
				sampledata.loc[sampledata['Sample_Name'].str.contains('.*STD\\d+.*|.*\\d+STD.*'), ['Description']] = 'Standard'
				sampledata.loc[sampledata['Sample_Name'].str.contains('.*STx\\d+.*|.*\\d+STx.*'), ['Description']] = 'Standard'
				sampledata.loc[sampledata['Sample_Name'].str.contains('.*STX\\d+.*|.*\\d+STX.*'), ['Description']] = 'Standard'
				sampledata.loc[sampledata['Sample_Name'].str.contains('.*CTL\\d+|CTLn|NTC.*'), ['Description']] = 'Control'
				sampledata.loc[sampledata['Sample_Name'].str.contains('.*ctl\\d+|ctln|ntc.*'), ['Description']] = 'Control'
				sampledata.loc[sampledata['Sample_Name'].str.contains('.*REF\\d+|REFn.*'), ['Description']] = 'Historic_Standard'
				print '\tWARNING: Sample Description has been infered. Please double-check output for validity'
			else:
				raise dawe.SSValidatorError(1333)
		
		# check Description
		sType = sampledata['Description']
		sType.replace('', np.nan, inplace=True)
		sType.dropna(inplace=True)
		sName = sampledata['Sample_Name']
		if (int(ss_infer_info) == 1):	
			sampledata['Description'] = [simpleCap(elem) for elem in sType]
			for i, j in zip(sName, sType):
				if re.search('STD|STx', str(i), flags=re.IGNORECASE):
					if not 'Standard' in str(j):
						print '\tWARNING: Potential Sample_Name: "' + str(i) + '" to Description: "' + str(j) + '" mismatch' 
				elif re.search('CTL|CTx|NTC', str(i), flags=re.IGNORECASE):
					if not 'Control' in str(j):
						print '\tWARNING: Potential Sample_Name: "' + str(i) + '" to Description: "' + str(j) + '" mismatch' 
				elif re.search('REF', str(i), flags=re.IGNORECASE):
					if not str(j) in ['Historic_Standard','Historical_Standard']:
					#if (not 'Historic_Standard' in str(j)) or (not 'Historical_Standard' in str(j)):
						print '\tWARNING: Potential Sample_Name: "' + str(i) + '" to Description: "' + str(j) + '" mismatch' 
	else:
		raise dawe.SSValidatorError(1332)
	
	# Source column
	if 'Source' in data_headers:
		# check column type
		try:
			sampledata['Source'] = sampledata['Source'].astype(str)
		except:
			raise dawe.SSValidatorError(1334)
		
		# check Source
		sName = sampledata['Sample_Name']
		sSource = sampledata['Source']
		if (int(ss_infer_info) == 1):
			sSource = ['P' if re.search('P|W|B', elem, flags=re.IGNORECASE) else elem for elem in sSource]
			for i, j in zip(sName, sSource):
				if re.search('-P-|-P$|-W-|-W$', str(i), flags=re.IGNORECASE):
					if not re.search( 'P|W|B', str(j), flags=re.IGNORECASE):
						print '\tWARNING: Potential Sample_Name: "' + str(i) + '" to Source: "' + str(j) + '" mismatch' 
				elif re.search('-U-|-U$', str(i), flags=re.IGNORECASE):
					if not re.search( 'U', str(j), flags=re.IGNORECASE):
						print '\tWARNING: Potential Sample_Name: "' + str(i) + '" to Source: "' + str(j) + '" mismatch' 
	else:
		raise dawe.SSValidatorError(1306)
		
	##### END OF MINIMALLY REQUIRED COLUMNS #####
	
	### CHECK INPUT, STANDARD_GROUP ###
	
	# Input column
	if 'Input' in data_headers:
		# check column type
		try:
			sampledata['Input'] = sampledata['Input'].astype(float)
		except:
			raise dawe.SSValidatorError(1340)
		
		# check Input
		if (int(ss_infer_info) == 1):
			for index, row in sampledata.iterrows():
				if re.search('P|W|B', str(row['Source']), flags=re.IGNORECASE):
					if not re.search('10', str(row['Input']), flags=re.IGNORECASE):
						print '\tWARNING: Potential Source: "' + str(row['Source']) + '" to Input: "' + str(row['Input']) + '" mismatch Sample_ID: "' + str(row['Sample_ID']) + '"'
				if re.search('U', str(row['Source']), flags=re.IGNORECASE):
					if not re.search('60', str(row['Input']), flags=re.IGNORECASE):
						print '\tWARNING: Potential Source: "' + str(row['Source']) + '" to Input: "' + str(row['Input']) + '" mismatch Sample_ID: "' + str(row['Sample_ID']) + '"'
	else:
		if (int(ss_infer_info) == 1):
			sampledata['Input'] = ''
			print '\tWARNING: Guessing "Input" from "Source". Please double-check output.'
			sampledata = checkSampleInput(sampledata)
		else: 
			raise dawe.SSValidatorError(1307)
	
	# Standard_Group column
	if 'Standard_Group' in data_headers:
		# check column type
		try:
			sampledata['Standard_Group'] = sampledata['Standard_Group'].astype(int)
		except:
			raise dawe.SSValidatorError(1341)
			
		# check Standard_Group
		inputs = []
		for index, row in sampledata.iterrows():
			key = row['Sample_Project'] + '-' + str(row['Input']) + '-' + row['Source']
			if str(key) not in inputs: 
				inputs.append(str(key))
		grps = sampledata['Standard_Group'].unique()
		if not (len(inputs) == len(grps)):
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Potential mismatch in "Standard_Group" column. Inferring "Standard_Group" from "Sample_Project","Source","Input". Please double-check output.'
				sampledata = checkStdGrp(sampledata)
			else:
				raise dawe.SSValidatorError(1343)
		else:
			print '\tFound and using "Standard_Group" column information'
	else:
		if (int(ss_infer_info) == 1):
			sampledata['Standard_Group'] = 0
			print '\tWARNING: Guessing "Standard_Group" from "Sample_Project","Source","Input". Please double-check output.'
			sampledata = checkStdGrp(sampledata)
		else:
			raise dawe.SSValidatorError(1312)
	
	### CHECK OTHER NOT AS IMPORTANT COLUMNS
	
	# Ng_Per_Rxn column
	if 'Ng_Per_Rxn' in data_headers:
		# check column type
		try:
			sampledata['Ng_Per_Rxn'] = sampledata['Ng_Per_Rxn'].astype(float)
		except:
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Not all rows have float type "Ng_Per_Rxn" value.'
			else:
				raise dawe.SSValidatorError(1335)
	else:
		if (int(ss_infer_info) == 1):
			sampledata['Ng_Per_Rxn'] = 'NA'
			print '\tWARNING: Filling in "NA" for "Ng_Per_Rxn" column...'
		else: 
			raise dawe.SSValidatorError(1315)
	
	# PhiX_Fraction column
	#print data_headers
	if 'PhiX_Fraction' in data_headers:
		# check column type
		try:
			sampledata['PhiX_Fraction'] = sampledata['PhiX_Fraction'].astype(float)
		except:
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Not all rows have float type "PhiX_Fraction" value.'
			else:
				raise dawe.SSValidatorError(1336)
	elif 'Phix_Fraction' in data_headers:
		# check column type
		try:
			sampledata['Phix_Fraction'] = sampledata['Phix_Fraction'].astype(float)
		except:
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Not all rows have float type "Phix_Fraction" value.'
			else:
				raise dawe.SSValidatorError(1336)
	else:
		if (int(ss_infer_info) == 1):
			sampledata['PhiX_Fraction'] = 'NA'
			print '\tWARNING: Filling in "NA" for "PhiX_Fraction" column...'
		else:
			raise dawe.SSValidatorError(1316)
	
	# Batch column
	if 'Batch' in data_headers:
		# check column type
		try:
			sampledata['Batch'] = sampledata['Batch'].astype(str)
		except:
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Not all rows have string type "Batch" value.'
			else:
				raise dawe.SSValidatorError(1337)
	else:
		if (int(ss_infer_info) == 1):
			sampledata['Batch'] = 'NA'
			print '\tWARNING: Filling in "NA" for "Batch" column...'
		else:
			raise dawe.SSValidatorError(1313)
	
	# Checkout_Number column
	if 'Checkout_Number' in data_headers:
		# check column type
		try:
			sampledata['Checkout_Number'] = sampledata['Checkout_Number'].astype(int)
		except:
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Not all rows have int type "Checkout_Number" value.'
			else:
				raise dawe.SSValidatorError(1338)
	else:
		if (int(ss_infer_info) == 1):
			sampledata['Checkout_Number'] = 'NA'
			print '\tWARNING: Filling in "NA" for "Checkout_Number" column...'
		else:
			raise dawe.SSValidatorError(1314)

	# Project_Version column
	if 'Project_Version' in data_headers:
		# check column type
		try:
			sampledata['Project_Version'] = sampledata['Project_Version'].astype(int)
		except:
			if (int(ss_infer_info) == 1):
				print '\tWARNING: Not all rows have int type "Project_Version" value.'
			else:
				raise dawe.SSValidatorError(1339)
	else:
		if (int(ss_infer_info) == 1):
			sampledata['Project_Version'] = 'NA'
			print '\tWARNING: Filling in "NA" for "Project_Version" column...'
		else:
			raise dawe.SSValidatorError(1317)
	
##############################################################################################
	
	# check if there are at least 3 standards per category (key off of Description == 'Standard', but check that there are 3 Sample_IDs without this -- common modification to drop standard is to set Description as 'Sample' for that standard)
	std_groups = sampledata.loc[sampledata['Description'].isin(['Standard','standard']), ['Sample_Project','Sample_Name','Source','Input','Standard_Group']].drop_duplicates()
	if (int(ss_infer_info) == 1):
		if all([sampledata.loc[ (sampledata['Sample_Project'] == std_groups.ix[i]['Sample_Project']) & 
								(sampledata['Sample_Name'] == std_groups.ix[i]['Sample_Name']) & 
								(sampledata['Source'] == std_groups.ix[i]['Source']) & 
								(sampledata['Standard_Group'] == std_groups.ix[i]['Standard_Group']) & 
								(sampledata['Input'] == std_groups.ix[i]['Input']) ].shape[0] >= 3 for i in std_groups.index]):
			print '\tFound minimum triplicates for all samples labeled as "Standard"'
		else:
			print '\tWARNING: Triplicates not found for all samples labeled as "Standard". Please double-check "Description" field for all samples. Trying to proceed anyway...'
			#raise dawe.SSValidatorError(1310)
	else:
		if not all([sampledata.loc[ (sampledata['Sample_Project'] == std_groups.ix[i]['Sample_Project']) & 
								(sampledata['Sample_Name'] == std_groups.ix[i]['Sample_Name']) & 
								(sampledata['Source'] == std_groups.ix[i]['Source']) & 
								(sampledata['Standard_Group'] == std_groups.ix[i]['Standard_Group']) & 
								(sampledata['Input'] == std_groups.ix[i]['Input']) ].shape[0] == 3 for i in std_groups.index]):
			raise dawe.SSValidatorError(1310)
		else:
			print '\tFound triplicates for all samples labeled as "Standard"'
			
	# check if there are at least 4 levels of STDs for each standard group
	std_groups = sampledata.loc[sampledata['Description'].isin(['Standard','standard']), ['Sample_Project','Sample_Name','Source','Input','Standard_Group']].drop_duplicates()
	if (int(ss_infer_info) == 1):
		if all(std_groups.groupby(['Sample_Project','Source','Input','Standard_Group'])['Sample_Name'].count() >= 4):
			print '\tFound at least 4 standard curve levels per standard group'
		else:
			print '\tWARNING: Did not find at least 4 standard curve levels per standard group. Trying to proceed anyway...'
	else:
		if not all(std_groups.groupby(['Sample_Project','Source','Input','Standard_Group'])['Sample_Name'].count() >= 4):
			raise dawe.SSValidatorError(1342)
		else:
			print '\tFound at least 4 standard curve levels per standard group'
		
	# variable number of standard MT levels for each assay, so just make sure that there is at least one (ensured to be in triplicate by check above)
	exp_groups = sampledata[['Sample_Project','Source','Input','Standard_Group']].drop_duplicates()
	if (int(ss_infer_info) == 1):
		if all([any(sampledata.loc[ (sampledata['Sample_Project'] == exp_groups.ix[i]['Sample_Project']) & 
									(sampledata['Source'] == exp_groups.ix[i]['Source']) & 
									(sampledata['Standard_Group'] == exp_groups.ix[i]['Standard_Group']) & 
									(sampledata['Input'] == exp_groups.ix[i]['Input']) ]['Description'].isin(['Standard','standard'])) for i in exp_groups.index]):
			print '\tAll samples have associated valid standard curves'
		else:
			print '\tWARNING: At lease one sample does not have a valid associated standard curve for the Assay/Source/Input/Standard_Group combination.'
	else:
		if not all([any(sampledata.loc[ (sampledata['Sample_Project'] == exp_groups.ix[i]['Sample_Project']) & 
									(sampledata['Source'] == exp_groups.ix[i]['Source']) & 
									(sampledata['Standard_Group'] == exp_groups.ix[i]['Standard_Group']) & 
									(sampledata['Input'] == exp_groups.ix[i]['Input']) ]['Description'].isin(['Standard','standard'])) for i in exp_groups.index]):
			#print '\tWARNING: Not all samples have associated standards. Trying to proceed anyway...'
			raise dawe.SSValidatorError(1311)
		else:
			print '\tAll samples have associated valid standard curves'
			
		
		
	if not basecalls_dir==None:
		# checkFastQFiles (returns fileList to files)
		files = getFastQList(basecalls_dir)
		
		if (files.shape[0] >= sampledata.shape[0]):
			print '\tMinimum Number of FastQ Files Matched ...'
		else:
			print '\tProblem matching FastQ files ...'
			raise dawe.SSValidatorError(1308)

		# (return to getSampleSheet)
		sampledata = checkFastQCache(files, sampledata)
		
		# getSampleAssay
		assaydata = getSampleAssay(sampledata, files)

		assayDf = sampledata[['Sample_Project','Source']].drop_duplicates()

		#print 'Sample sheet has been validated'
		
		# list:    data  ,	record	  , files,   assays , summary,    (new)
		return sampledata, samplesheet, files, assaydata, assayDf, sampleheader
	else:
		return sampledata, samplesheet, sampleheader

def checkSSNames(data_headers):
	# remove blank entries
	data_headers = filter(None, data_headers)
	data_headers = [re.sub('\bTotal ng\b|^\bInput ng\b|^ng$', 'Ng_Per_Rxn', str(header), flags=re.IGNORECASE) for header in data_headers]
	data_headers = [simpleCap2(header, '_') for header in data_headers]
	data_headers = [re.sub('Id', 'ID', header, flags=re.IGNORECASE) for header in data_headers]
	return data_headers

def simpleCap(x):
	s = x.split(" ")[0]
	return "".join([s[0].upper(),s[1:].lower()])

def simpleCap2(x, schar):
	s = x.split(schar)
	ss = [''.join([ss[0].upper()]+[ss[1:].lower()]) for ss in s]
	return schar.join(ss)

def checkAssayType(assay):
	assay = ['EGFR_L858R' if re.search('L858R', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['EGFR_T790M' if re.search('T790M', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['EGFR_EX19DEL' if re.search('Ex19|Exon19', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['BRAF_V600X' if re.search('BRAF', elem, flags=re.IGNORECASE) and not re.search('_2', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['BRAF_V600X_2' if re.search('BRAF2|BRAF_*_2', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['KRAS_G12X' if re.search('KRAS', elem, flags=re.IGNORECASE) and not re.search('RH|Q61', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['KRAS_Q61X' if re.search('KRAS', elem, flags=re.IGNORECASE) and not re.search('RH|G12', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['KRAS_G12X_2' if re.search('RH|KRAS2|KRAS_*_2', elem, flags=re.IGNORECASE) else elem for elem in assay]
	assay = ['NRAS_Q61X' if re.search('NRAS', elem, flags=re.IGNORECASE) else elem for elem in assay]
	return assay

def checkAssaySource(sdata, assays):
	print 'Guessing Sample Source..., please verify the sample sheet record generated.'
	# NOTE: default is U if not found
	sdata['Source'] = sdata['Source'].astype(str)
	sdata['Source'].fillna('U', inplace=True)

	# NOTE: should this be done on an individual sample basis, and not the entire run??
	if [re.search('-P-|-P$|-W-|-W$', name) for name in sdata['Sample_Name']]:
		sdata['Source'] = ['P'] * sdata.shape[0]
	elif [re.search('-U-|-U$', name) for name in sdata['Sample_Name']]:
		sdata['Source'] = ['U'] * sdata.shape[0]

	if 'Input' in sdata.columns:
		# TODO: check that input is an integer for this comparison -- WRONG: float!  can be 10, 10.1, etc
		sdata.loc[ sdata['Input'] == '10', ['Source']] = 'P'
		sdata.loc[ sdata['Input'] == '60', ['Source']] = 'U'

	return sdata
	
def checkStdGrp(sdata):
	#print 'Guessing Standard Groups..., please verify the sample sheet record generated.'
	sdata['Standard_Group'] = sdata['Standard_Group'].astype(int)
	sdata['Standard_Group'].fillna('2', inplace=True)
	
	# NOTE: default is 1 if not found
	# find unique number of Assay_Input_Source combo
	inputs = []
	for index, row in sdata.iterrows():
		key = row['Sample_Project'] + '-' + str(row['Input']) + '-' + row['Source']
		if str(key) not in inputs: 
			inputs.append(str(key))
			
	
	grpCount = 1
	for i in inputs:
		#print i, grpCount
		info = i.split("-")
		sdata.loc[ (sdata['Sample_Project'] == str(info[0])) & (sdata['Input'].astype(str) == str(info[1])) & (sdata['Source'] == str(info[2])), 'Standard_Group' ] = int(grpCount)
		grpCount = grpCount + 1
	
	return sdata

def fillNA(sdata, columnName):
	
	# NOTE: default is NA if not found
	sdata[columnName] = sdata[columnName].astype(str)
	sdata[columnName].fillna('NA', inplace=True)
	
	return sdata

def checkSampleSource(sSource):
	sSource = ['U' if re.search('Urine|u', elem, flags=re.IGNORECASE) else elem for elem in sSource]
	sSource = ['P' if re.search('Plasma|p|B', elem, flags=re.IGNORECASE) else elem for elem in sSource]
	sSource = ['P' if re.search('Streck|W', elem, flags=re.IGNORECASE) else elem for elem in sSource]
	return sSource

def checkSampleInput(sdata):
	sdata['Input'] = ['60'] * sdata.shape[0]		# default to urine
	sdata['Input'] = ['60' if re.search('U', r['Source'], flags=re.IGNORECASE) else r['Input'] for i,r in sdata.iterrows()]
	sdata['Input'] = ['10' if re.search('P|W|B', r['Source'], flags=re.IGNORECASE) else r['Input'] for i,r in sdata.iterrows()]
	return sdata

def getFastQList(basecalls_dir):
	files = [f for f in os.listdir(basecalls_dir) if os.path.isfile(os.path.join(basecalls_dir, f)) and re.search('\.fastq\.gz', f)]
	fileList = pd.DataFrame([elem.split('_') for elem in files])
	fileList.columns = ['Sample_Name', 'Sample_ID', 'Lane_Number', 'Read_Number', 'Extension']
	fileList['Files'] = files
	fileList['Sample_ID'] = [re.sub('S', '', elem) for elem in fileList['Sample_ID']]
	# NOTE: need to make sure Sample_ID is integer before sorting/merging/etc.
	fileList['Sample_ID'] = fileList['Sample_ID'].astype(int)
	fileList = fileList.sort_values(['Sample_ID'], ascending=[False])
	return fileList

def makeListfromCache(csv_cache):
	# TODO: does reading in require quote = "\'" and stringsAsFactors = False?
	dat = pd.read_csv(csv_cache)
	files = dat[dat['id'] != 'Undetermined', ['id', 'Snumber']]
	files.columns = ['Sample_Name','Sample_ID']
	files['Lane_Number'] = ['L001'] * files.shape[0]
	files['Read_Number'] = ['R1'] * files.shape[0]
	files['Extension'] = ['fastq.gz'] * files.shape[0]
	files['Files'] = [''] * files.shape[0]
	return files

def checkFastQCache(fileList, sampledata):
	#sampleFile = pd.merge(sampledata, fileList[fileList['Sample_Name'] != 'Undetermined'], how='inner', left_on='Sample_ID', right_on='Sample_ID')
	sampleFile = pd.merge(sampledata, fileList[fileList['Sample_Name'] != 'Undetermined'], how='inner', on='Sample_ID')
	colsWanted = sampledata.columns
	colsTemp = [re.sub('Sample_Name', 'Sample_Name_x', elem) for elem in colsWanted]		# NOTE: dataframe is appended after underscore (not dot) in python
	merged_sorted_data = sampleFile.sort_values(by=['Sample_ID'], ascending=[True])
	merged_sorted_data = merged_sorted_data[colsTemp]
	merged_sorted_data.columns = colsWanted
	return merged_sorted_data

def getSampleAssay(sampledata, files):
	#print sampledata
	ssFileNum = sampledata.shape[0]
	dirFileNum = files[files['Sample_Name'] != 'Undetermined'].shape[0]
	if (ssFileNum != dirFileNum):
		print 'Potential File Number Mismatch ...'
	# sampleFile = pd.merge(sampledata, files[files['Sample_Name'] != 'Undetermined'], how='inner', left_on=['Sample_ID','Sample_Name'], right_on=['Sample_Name','Sample_ID'])
	sampleFile = pd.merge(sampledata, files[files['Sample_Name'] != 'Undetermined'], how='inner', on=['Sample_ID','Sample_Name'])
	sampleFile = sampleFile.sort_values(by=['Sample_ID'], ascending=[True])
	#print sampleFile
	mergeFileNum = sampleFile.shape[0]
	if (ssFileNum != mergeFileNum):
		print 'Potential File Name Mismatch'
	#assays = sampleFile[['Sample_Project','Source']].unique()		# deprecated for dfrm's
	assays = sampleFile[['Sample_Project','Source']].drop_duplicates()
	mylist = pd.concat([sampleFile.loc[(sampleFile['Sample_Project'] == r[0]) & (sampleFile['Source'] == r[1])] for i,r in assays.iterrows()])
	return mylist

#def runSSV( basecalls_dir, sample_sheet, runid, ss_outfile, ss_infer_info ):
def runSSV( sample_sheet, ss_outfile, ss_infer_info, basecalls_dir=None, runid=None ):
	print 'SampleSheetValidator module version is " ' + VERSION + ' "\n'

	# TrovaPipe only uses assays and summary (loaded into SampleInfo list)
	#   data  ,	  record   , files,   assays , summary,    (new)
	
	if (not basecalls_dir==None) and (not runid==None) :
		sampledata, samplesheet, files, assaydata, assayDf, sampleheader = validate_sample_sheet(sample_sheet, ss_infer_info, basecalls_dir)
	else:
		sampledata, samplesheet, sampleheader = validate_sample_sheet(sample_sheet, ss_infer_info)
	
	# writeSSV (validated sample sheet)
	valid_ss = sampleheader
	# append any extra rows that were added to sampledata (e.g. Source, Input)
	valid_ss = pd.concat([valid_ss, pd.DataFrame([],index=valid_ss.index, columns=range(sampledata.shape[1]-sampleheader.shape[1])).fillna('')], axis=1)
	valid_ss.columns = sampledata.columns 	# need to have same headers to append
	
	#valid_ss = pd.concat([sampleheader, sampledata])
	column_names = pd.DataFrame(sampledata.columns).T
	column_names.columns = sampledata.columns
	valid_ss = valid_ss.append(column_names)
	valid_ss = valid_ss.append(sampledata)
	
	try:
		print
		print '\tWriting validated sample sheet to:', ss_outfile
		valid_ss.to_csv(ss_outfile, index=False, header=False)		
	except:
		print "Unexpected error:", sys.exc_info()[0]
		raise Exception("Unexpected error:", sys.exc_info()[0])

	# write SampleSheet_Used_
	# NOTE: write SampleSheet_Used_ to results_dir location, not TrovaPipe's seqPath
	#print 'Writing original sample sheet to:',ssu_outfile
	#samplesheet.to_csv(ssu_outfile, index=False, header=False)

	# write assaydata
	#ss_assaydata_outfile = os.path.join(os.path.dirname(ss_outfile),'assaydata_'+runid+'.csv')
	#print 'Writing assaydata data frame to :',ss_assaydata_outfile
	#assaydata.to_csv(ss_assaydata_outfile, index=False, header=True)

	# # write assayDf -- NO, only need assaydata
	# ss_assayDf_outfile = os.path.join(os.path.dirname(ss_outfile),'assayDf_'+runid+'.csv')
	# print 'Writing assayDf data frame to :',ss_assayDf_outfile
	# assayDf.to_csv(ss_assayDf_outfile, index=False, header=True)
	
	return 0

def test_ssv():
	# runid = '160523_M02001_0494_000000000-APFM8_10ng_KB'
	runid = '160603_M02637_0479_000000000-APBRL'
	# runid = '160614_M02001_0501_000000000-APFD2'
	# runid = '160614_M02001_0501_1_bad_runid'			# no basecalls_dir
	# runid = '160614_M02001_0501_100000000_bad_ss'		# no basecalls_dir

	if (sys.platform == 'linux2'):
		sample_sheet = '/mnt/rnd/users/mwhidden/BI-125/data/'+runid+'/SampleSheet.csv'
		ss_outfile = '/mnt/rnd/users/mwhidden/BI-125/modified/output/ssv_output/'+runid+'/'+runid+'_sheet.csv'
	elif (sys.platform == 'darwin'):
		sample_sheet = '/Volumes/RND/users/mwhidden/BI-125/data/'+runid+'/SampleSheet.csv'
		ss_outfile = '/Volumes/RND/users/mwhidden/BI-125/modified/output/ssv_output/'+runid+'/'+runid+'_sheet.csv'
	else:
		print 'Unknown OS.  Exiting...'
		sys.exit(2)

	ssu_outfile = os.path.join(os.path.dirname(ss_outfile),'SampleSheet_Used_'+runid+'.csv')

	basecalls_dir = os.path.abspath(os.path.join(sample_sheet, '..','Data','Intensities','BaseCalls'))
	csv_cache = None
	print 'Basecalls_dir:',basecalls_dir

	#ss_infer_info = 0	 	# just checks for critical info and does not change anything, except for Sample_Name conversion based on Illumina protocol
	ss_infer_info = 1		# infers info from other sample sheet info as well, according to Wilfred's original validator
	
	# TrovaPipe only uses assays and summary (loaded into SampleInfo list)
	#   data  ,	  record   , files,   assays , summary,    (new)
	sampledata, samplesheet, files, assaydata, assayDf, sampleheader = validate_sample_sheet(sample_sheet, basecalls_dir, csv_cache, ss_infer_info)

	# writeSSV (validated sample sheet)
	print 'Writing validated sample sheet to:',ss_outfile
	valid_ss = sampleheader
	# append any extra rows that were added to sampledata (e.g. Source, Input)
	valid_ss = pd.concat([valid_ss, pd.DataFrame([],index=valid_ss.index, columns=range(sampledata.shape[1]-sampleheader.shape[1])).fillna('')], axis=1)
	valid_ss.columns = sampledata.columns 	# need to have same headers to append
	#valid_ss = pd.concat([sampleheader, sampledata])
	column_names = pd.DataFrame(sampledata.columns).T
	column_names.columns = sampledata.columns
	valid_ss = valid_ss.append(column_names)
	valid_ss = valid_ss.append(sampledata)
	valid_ss.to_csv(ss_outfile, index=False, header=False)

	# write SampleSheet_Used_
	# NOTE: write SampleSheet_Used_ to results_dir location, not TrovaPipe's seqPath
	print 'Writing original sample sheet to:',ssu_outfile
	samplesheet.to_csv(ssu_outfile, index=False, header=False)

	# write assaydata
	ss_assaydata_outfile = os.path.join(os.path.dirname(ss_outfile),'assaydata_'+runid+'.csv')
	print 'Writing assaydata data frame to :',ss_assaydata_outfile
	assaydata.to_csv(ss_assaydata_outfile, index=False, header=True)

	# # write assayDf -- NO, only need assaydata
	# ss_assayDf_outfile = os.path.join(os.path.dirname(ss_outfile),'assayDf_'+runid+'.csv')
	# print 'Writing assayDf data frame to :',ss_assayDf_outfile
	# assayDf.to_csv(ss_assayDf_outfile, index=False, header=True)

# for use as a script
if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
