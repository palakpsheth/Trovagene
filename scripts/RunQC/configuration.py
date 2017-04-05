#!/usr/bin/env python
import sys
import os

class SampleInfo :

	def __init__( self , basecalls_dir , sample_id , sample_name , reads ):
		
		# Handle illegal sample sheet characters
		sample_name = sample_name.replace( "_" , "-" )
		sample_name = sample_name.replace( "." , "-" )
		sample_name = sample_name.replace( " " , "-" )
		sample_name = sample_name.replace( "+" , "-" )
		sample_name = sample_name.replace( "(" , "-" )
		sample_name = sample_name.replace( ")" , "-" )
		sample_name = sample_name.replace( "#" , "-" )
		sample_name = sample_name.replace( "*" , "-" )
		sample_name = sample_name.replace( "/" , "-" )
		sample_name = sample_name.replace( "\\" , "" )
		sample_name = sample_name.replace( "?" , "" )
		sample_name = sample_name.replace( "$" , "" )
		sample_name = sample_name.replace( "%" , "" )
		sample_name = sample_name.replace( ":" , "-" )
		while '--' in sample_name :
			sample_name = sample_name.replace( "--" , "-" )
		
		if sample_name.endswith('-') : sample_name = sample_name[ : len( sample_name ) - 1 ]
		
		# Extrapolate Read-1 filename
		self.read_1_fastq = os.path.join( basecalls_dir , sample_name + '_' + 'S' + sample_id + '_L001_R1_001.fastq.gz' )
		if reads == 2 : # Extrapolate Read-2 filename
			self.read_2_fastq = os.path.join( basecalls_dir , sample_name + '_' + 'S' + sample_id + '_L001_R2_001.fastq.gz' )
	
class Config :

	def __init__( self , basecalls_dir ):

		self.instrument_type = "miseq"
		self.basecalls_dir = basecalls_dir
		self.is_paired_end , self.sampleInfoDictionary = self.getSampleInfoDictionary( basecalls_dir )
		self.run_root = basecalls_dir.split('/Data/Intensities/BaseCalls')[ 0 ]
		self.flowcellID = os.path.basename( self.run_root.split( '_' )[ -1 ] )
		self.runID = self.run_root.split(os.sep)[-1]
		self.irunID = self.runID[:34]
		
	# Just getting Fastq File info
	def getSampleInfoDictionary( self , basecalls_dir ) :
	
		sampleInfoDictionary = {}
	
		path_element_list = basecalls_dir.split( 'Data' + os.path.sep + 'Intensities' + os.path.sep + 'BaseCalls' )
		sampleSheet = os.path.join( path_element_list[0] , 'SampleSheet.csv' )
		
		if not os.path.exists( sampleSheet ) : return False , sampleInfoDictionary
		
		foundReads = False
		foundData  = False
		foundHeaders = False
		readsCount = 0
		
		sampleCount = 1
		sampleIDIndex = -1
		sampleNameIndex = -1 
		orientationIndex = -1
		
		sampleID_integer = 1
		
		for line in open( sampleSheet , 'rb' ) :
			line = line.strip().split(',')
			if foundData and foundHeaders and ( len( line ) == 0 or line[0] == "" ) : break
			if '[Reads]' in line : 
				foundReads = True
				continue
			elif '[Data]' in line :
				foundData = True
				continue
			elif foundReads and not foundData :
				if line[0].isdigit() :
					readsCount += 1
			elif foundData and not foundHeaders :
				element_count = 0
				# do not parse the sample_id from the sample sheet.  Often they are non-sequential
				# integers and the illumina software ignores those.  derive the integers on our own.
				for element in line :
					if 'Sample_Name' in element :
						sampleNameIndex = element_count
					elif 'Orientation' in element :
						orientationIndex = element_count
					element_count += 1
				foundHeaders = True
			elif foundData and foundHeaders:
				sampleInfo = SampleInfo( basecalls_dir , str( sampleID_integer ) , line[ sampleNameIndex ] , readsCount )
				sampleInfoDictionary[ sampleCount ] = sampleInfo
				sampleCount += 1
				sampleID_integer += 1
				
		is_paired_end = False
		if readsCount == 2 : is_paired_end = True 
				
		return is_paired_end , sampleInfoDictionary
