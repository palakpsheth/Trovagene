#!/usr/bin/env python
from __future__ import division
import sys, os
from scripts.RunQC.Utilities import FileUtils as fileUtils
import xml.etree.ElementTree as ET
from scripts.RunQC.Metrics.TileMetrics import TileMetrics
from scripts.RunQC.Metrics.ErrorMetrics import ErrorMetrics

class MiSeqRunQualityInfo :

	# Checks phix alignment error rate
	def EvaluateErrorMetrics( self , config ) :
		
		path_element_list = config.basecalls_dir.split( 'Data' + os.path.sep + 'Intensities' + os.path.sep + 'BaseCalls')
		interop_path      = os.path.join( path_element_list[0] , 'InterOp' )
		error_metrics_file = os.path.join( interop_path , 'ErrorMetricsOut.bin' )
		
		if os.path.exists( error_metrics_file ) :
		
			metrics = ErrorMetrics( error_metrics_file )
			self.setAveragePhixErrorRate( metrics.average_error_rate )
		

	# calculates average percent failure amongst all tiles
	def CalculatePercentFailedDemux( self , config ) :

		alignment_dir = fileUtils.AlignmentDirectoryFromBaseCalls( config.basecalls_dir )
			
		demux_report  = os.path.join( alignment_dir , "DemultiplexSummaryF1L1.txt" )
		
		exists , message = fileUtils.exists( demux_report )
		
		if exists :
			
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
			
			self.setPercentFailedDemux( average_percent_failed )
			
	# Checks for percentage of tiles where zero reads demux.
	# Can indicate a problem with the flowcell - large spots, dust inhibiting image analysis or
	# it's also been seen when data is moved while it's being analyzed
	def CalculatePercentTileDemuxFail( self , config ) :

		alignment_dir = fileUtils.AlignmentDirectoryFromBaseCalls( config.basecalls_dir )
			
		demux_report  = os.path.join( alignment_dir , "DemultiplexSummaryF1L1.txt" )
		
		exists , message = fileUtils.exists( demux_report )
		
		if exists :
			
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
				average_percent_failed = ( zero_tiles / total_tiles ) * 100
			else : average_percent_failed = 100
			
			self.setPercentTilesFailedDemux( average_percent_failed )
	

	# Checks for things like flow cell density etc.
	def EvaluateTileMetrics( self , config ) :

		path_element_list = config.basecalls_dir.split( 'Data' + os.path.sep + 'Intensities' + os.path.sep + 'BaseCalls')
		interop_path      = os.path.join( path_element_list[0] , 'InterOp' )
		
		tile_metrics_file = os.path.join( interop_path , 'TileMetricsOut.bin' )
		
		if os.path.exists( tile_metrics_file ) :
		
			metrics = TileMetrics( tile_metrics_file )
			
			self.setAverageDensity( metrics.average_density )
			self.setAverageDensityPF( metrics.average_density_pf )
			self.setPhasingApplied( metrics.average_phasing )
			self.setPrephasingApplied( metrics.average_prephasing )
			self.setPercentPhiXAligned( metrics.average_phix_aligned )
			self.setClusterCountPF( metrics.total_pf_clusters )
			self.setPercentPF( metrics.Get_Percent_PF() )
		
	# Sanity Check Fastq Files
	def VerifyFastqFilesExist( self , config ) :
		
		fastq_files_exist = True
		message = "File not found"
		
		for sampleNumber , sampleInfo in config.sampleInfoDictionary.iteritems() :
			fastq_files_exist , message = fileUtils.exists( sampleInfo.read_1_fastq )
			if not fastq_files_exist : break
			if config.is_paired_end :
				fastq_files_exist , message = fileUtils.exists( sampleInfo.read_2_fastq )
				if not fastq_files_exist : break
				
		self.setFastqFilesExist( fastq_files_exist , message )
		
	# Checks that the instrument completed
	# demux & fastq file generation
	def VerifyPrimaryAnalysisComplete( self , config ) :

		illumina_alignment_dir = fileUtils.AlignmentDirectoryFromBaseCalls( config.basecalls_dir )
		checkpoint_file        = os.path.join( illumina_alignment_dir, "Checkpoint.txt" )
		
		if os.path.exists( checkpoint_file ) :	
			
			f = open( checkpoint_file , 'rb')
			line = f.readline().strip()
			f.close()
			
			step = int( line )
			
			if step >= 3 : self.setPrimaryAnalysisComplete( True , step )
			else : self.setPrimaryAnalysisComplete( False , step )
		
	# Warn if unknown illumina SW is detected.  
	# sometimes they ship products that are not
	# ready for prime time - we should detect that
	def VerifyIlluminaSoftwareVersions( self , config ) :
			
		versions_file = os.path.join( os.path.dirname( __file__ ) , 'instrument_software_versions.xml' )
		
		if os.path.exists( versions_file  ) :
		
			known_versions_used = True
			
			tree = ET.parse( versions_file )
			root = tree.getroot()
			
			FPGA_versions = list()
			MCS_versions  = list()
			RTA_versions  = list()
			MSR_versions  = list()
			
			for version in root.findall( "./FPGA_versions/version" ) : # hardware
				FPGA_versions.append( version.text )
			for version in root.findall( "./MCS_versions/version" ) :  # firmware
				MCS_versions.append( version.text )
			for version in root.findall( "./RTA_versions/version" ) :  # real time anlaysis sw ( primary analysis )
				RTA_versions.append( version.text )
			for version in root.findall( "./MSR_versions/version" ) :  # miseq reporter ( secondary analysis )
				MSR_versions.append( version.text )
								
			versions = dict()
		
			versions['fpga_version'] = "unknown"
			versions['mcs_version']  = "unknown"
			versions['rta_version']  = "unknown"
			versions['msr_version']  = "unknown"
		
			# first 3 are read from run params file
			path_element_list = config.basecalls_dir.split( 'Data' + os.path.sep + 'Intensities' + os.path.sep + 'BaseCalls' )
			runParametersFile = os.path.join( path_element_list[0], 'RunParameters.xml' )
			if not os.path.exists( runParametersFile ) :
				runParametersFile = os.path.join( path_element_list[0], 'runParameters.xml' ) # sometimes it's lowercase!
			
			if os.path.exists( runParametersFile ) :
			
				tree = ET.parse( runParametersFile )
				root = tree.getroot()
			
				for child in root:
					if child.tag == "FPGAVersion" :
						versions['fpga_version'] = child.text
					elif child.tag == "MCSVersion" :
						versions['mcs_version'] = child.text
					elif child.tag == "RTAVersion" :
						versions['rta_version'] = child.text
						
			# Miseq reporter writes to generate fastq stats file
			generateFastqStatsFile = os.path.join( fileUtils.AlignmentDirectoryFromBaseCalls( config.basecalls_dir ) , 'GenerateFASTQRunStatistics.xml' )
			
			if os.path.exists( generateFastqStatsFile ) :
		
				tree = ET.parse( generateFastqStatsFile )
				root = tree.getroot()
				
				for child in root:
					if child.tag == "RunStats" :
						msr_element = child.find('AnalysisSoftwareVersion')
						versions['msr_version'] = msr_element.text
					
				if versions['fpga_version'] not in FPGA_versions :
					known_versions_used = False
				if versions['mcs_version'] not in MCS_versions :
					known_versions_used = False
				if versions['rta_version'] not in RTA_versions :
					known_versions_used = False
				if versions['msr_version'] not in MSR_versions :
					known_versions_used = False
						
				self.setMiSeqSWVersions( known_versions_used , versions )
	
	# Given a base call dir, write the report
	def writeReport( self , config , version, working_dir ) :
		
		#file = open( os.path.join( config.run_root , "RunQuality_" + config.flowcellID + ".csv" ) , 'wb' )
		if not os.path.exists( os.path.join( working_dir , config.runID ) ):
			os.makedirs( os.path.join( working_dir , config.runID ) )
		file = open( os.path.join( working_dir , config.runID, config.runID + "_stats.csv" ) , 'wb' )
	
		file.write( "FLAG,METRIC,QUALITY_SCORE,MESSAGE,VERSION,RUN_ID\n" )
		#file.write( "Instrument Software Check" +
				#',' + 'N/A' + 
				#',' + str( self.known_sw_versions_used_score ) +
				#',' + self.known_sw_versions_used_msg +
				#',' + version + 
				#',' + config.flowcellID + '\n' )
		#file.write( "Fastq File Sanity Check" +
				#',' + 'N/A' +
				#',' + str( self.fastq_files_score ) +
				#',' + self.fastq_files_exist_msg +
				#',' + version + 
				#',' + config.flowcellID + '\n' )
		#file.write( "Instrument Run Complete" +
				#',' + str( self.last_primary_analysis_step ) + 
				#',' + str( self.primary_analysis_complete_score ) +
				#',' + self.primary_analysis_complete_msg +
				#',' + version +
				#',' + config.flowcellID + '\n' )
		file.write( "Phasing" +
				',' + str( "%0.2f" % self.average_phasing ) +
				',' + str( self.phasing_score )  +
				',' + self.phasing_msg +
				',' + version + 
				',' + config.irunID + '\n' )
		file.write( "Prephasing" +
				',' + str( "%0.2f" % self.average_prephasing ) +
				',' + str( self.prephasing_score )  +
				',' + self.prephasing_msg +
				',' + version +
				',' + config.irunID + '\n' )
		file.write( "PhiX Control Error Rate" +
				',' + str( "%0.2f" % self.average_phix_error_rate ) +
				',' + str( self.average_phix_error_rate_score )  +
				',' + self.average_phix_error_rate_msg +
				',' + version +
				',' + config.irunID + '\n' )
		file.write( "Percent PF"
				',' + str( "%0.2f" % self.percent_pf ) +
				',' + str( self.percent_pf_score ) +
				',' + self.percent_pf_msg +
				',' + version + 
				',' + config.irunID + '\n' )
		file.write( "Cluster Density" +
				',' + str( int( self.cluster_density ) ) +
				',' + str( self.cluster_density_score ) +
				',' + self.cluster_density_msg +
				',' + version +
				',' + config.irunID + '\n' )				
		file.write( "Cluster Density PF" +
				',' + str( int( self.cluster_density_pf ) ) +
				',' + str( self.cluster_density_pf_score ) +
				',' + self.cluster_density_pf_msg +
				',' + version +
				',' + config.irunID + '\n' )
		file.write( "Reads PF" +
				',' + str( self.total_pf_clusters ) +
				',' + str( self.reads_pf_score ) +
				',' + self.reads_pf_msg +
				',' + version + 
				',' + config.irunID + '\n' )
		file.write( "Percent PhiX Aligned" +
				',' + str( "%0.2f" % self.average_phix_aligned ) +
				',' + str( self.percent_phix_aligned_score ) +
				',' + self.percent_phix_aligned_msg +
				',' + version +
				',' + config.irunID + '\n' )				
		file.write( "Percent Failed Demux" +
				',' + str( "%0.2f" % self.average_demux_failed ) +
				',' + str( self.percent_demux_failed_score ) +
				',' + self.percent_demux_failed_msg +
				',' + version + 
				',' + config.irunID + '\n' )
		file.write( "Percent Tiles Failed Demux" +
				',' + str( "%0.2f" % self.percent_tile_demux_fail ) +
				',' + str( self.percent_tile_demux_fail_score ) +
				',' + self.percent_tile_demux_fail_msg +
				',' + version +
				',' + config.irunID + '\n' )
		file.close()
		
	# Given a base call dir, write the report
	def writeReport2( self , config , version, working_dir ) :
		
		#file = open( os.path.join( config.run_root , "RunQuality_" + config.flowcellID + ".csv" ) , 'wb' )
		if not os.path.exists( os.path.join( working_dir , config.runID ) ):
			os.makedirs( os.path.join( working_dir , config.runID ) )
		file = open( os.path.join( working_dir , config.runID, config.runID + "_stats.csv" ) , 'ab' )
	
		file.write( "RunId,Tool,FLAG,StandardGroup,Type,Metric,Comments\n" )
		wantedMetricsNames = ['Phasing','Prephasing','PhiX Control Error Rate','Percent PF','Cluster Density','Cluster Density PF','Reads PF','Percent PhiX Aligned','Percent Failed Demux','Percent Tiles Failed Demux']
		wantedMetricsVariables = ['average_phasing','average_prephasing','average_phix_error_rate','percent_pf','cluster_density','cluster_density_pf','total_pf_clusters','average_phix_aligned','average_demux_failed','percent_tile_demux_fail']
		wantedMetricsMsgs = ['phasing_msg','prephasing_msg','average_phix_error_rate_msg','percent_pf_msg','cluster_density_msg','cluster_density_pf_msg','reads_pf_msg','percent_phix_aligned_msg','percent_demux_failed_msg','percent_tile_demux_fail_msg']
		
		if len(wantedMetricsNames) == len(wantedMetricsVariables) == len(wantedMetricsMsgs)  :
			for index,MetricName in enumerate(wantedMetricsNames):
				MetricVariable = wantedMetricsVariables[index]
				MetricMsg = wantedMetricsMsgs[index]
				
				file.write( config.irunID +
					',' + version +
					',' + MetricName +
					',' + 'ALL' +
					',' + 'ALL' +
					',' + str( "%0.2f" % self.__dict__[MetricVariable] ) +
					',' + self.__dict__[MetricMsg] + '\n'
				)
		
		file.close()
	
	
	# Average error rate from RTA SeqAn alignment of phix
	def setAveragePhixErrorRate( self , average_error_rate ) :

		self.average_phix_error_rate = average_error_rate
		
		if average_error_rate <= self.max_error_rate :
			self.average_phix_error_rate_msg = "PhiX Error Rate [spec: <= " + str( "%.2f" % self.max_error_rate ) + "]: " + str( "%.2f" % average_error_rate )
			self.average_phix_error_rate_ok = True
			self.average_phix_error_rate_score = 10
			
		else :
			self.average_phix_error_rate_ok = True
			self.average_phix_error_rate_msg = "PhiX Error Rate is greater than spec [spec: <= " + str( "%.2f" % self.max_error_rate ) + "]: " + str( "%.2f" % average_error_rate )

			if average_error_rate > self.max_error_rate and average_error_rate <= self.max_error_rate + 0.1 : self.average_phix_error_rate_score = 9 
			elif average_error_rate > self.max_error_rate + 0.1 and average_error_rate <= self.max_error_rate + 0.2 : self.average_phix_error_rate_score = 8 
			elif average_error_rate > self.max_error_rate + 0.2 and average_error_rate <= self.max_error_rate + 0.3 : self.average_phix_error_rate_score = 7 
			elif average_error_rate > self.max_error_rate + 0.3 and average_error_rate <= self.max_error_rate + 0.4 : self.average_phix_error_rate_score = 6 
			elif average_error_rate > self.max_error_rate + 0.4 and average_error_rate <= self.max_error_rate + 0.5 : self.average_phix_error_rate_score = 5 
			elif average_error_rate > self.max_error_rate + 0.5 and average_error_rate <= self.max_error_rate + 0.6 : self.average_phix_error_rate_score = 4 
			elif average_error_rate > self.max_error_rate + 0.6 and average_error_rate <= self.max_error_rate + 0.7 : self.average_phix_error_rate_score = 3 
			elif average_error_rate > self.max_error_rate + 0.7 and average_error_rate <= self.max_error_rate + 0.8 : self.average_phix_error_rate_score = 2 
			elif average_error_rate > self.max_error_rate + 0.8 : self.average_phix_error_rate_score = 1 ; self.average_phix_error_rate_ok = False
		
	# Average demux failure percent amongst all tiles
	def setPercentFailedDemux( self , average_percent_failed ) :
		
		self.average_demux_failed = average_percent_failed
		
		if average_percent_failed <= self.max_mean_demux_failure :
		
			self.percent_demux_failed_msg = "Average percent demux failure is within spec [spec: <= " + str( self.max_mean_demux_failure ) + "]: " + str( "%.2f" % average_percent_failed )
			self.percent_demux_failed_ok = True
			self.percent_demux_failed_score = 10
			
		else :
			self.percent_demux_failed_ok = True
			self.percent_demux_failed_msg = "Average percent demux failure is greater than spec [spec: <= " + str( self.max_mean_demux_failure ) + "]: " + str( "%.2f" % average_percent_failed)
			self.percent_demux_failed_score = 10

			if average_percent_failed > self.max_mean_demux_failure         and average_percent_failed < self.max_mean_demux_failure + 3  : self.percent_demux_failed_score = 9
			elif average_percent_failed >= self.max_mean_demux_failure + 3  and average_percent_failed < self.max_mean_demux_failure + 7  : self.percent_demux_failed_score = 8
			elif average_percent_failed >= self.max_mean_demux_failure + 7  and average_percent_failed < self.max_mean_demux_failure  + 11 : self.percent_demux_failed_score = 7
			elif average_percent_failed >= self.max_mean_demux_failure + 11 and average_percent_failed < self.max_mean_demux_failure + 14 : self.percent_demux_failed_score = 6
			elif average_percent_failed >= self.max_mean_demux_failure + 14 and average_percent_failed < self.max_mean_demux_failure + 16 : self.percent_demux_failed_score = 5
			elif average_percent_failed >= self.max_mean_demux_failure + 16 and average_percent_failed < self.max_mean_demux_failure + 18 : self.percent_demux_failed_score = 4
			elif average_percent_failed >= self.max_mean_demux_failure + 18 and average_percent_failed < self.max_mean_demux_failure + 22 : self.percent_demux_failed_score = 3 
			elif average_percent_failed >= self.max_mean_demux_failure + 22 and average_percent_failed < self.max_mean_demux_failure + 25 : self.percent_demux_failed_score = 2
			elif average_percent_failed >= self.max_mean_demux_failure + 25 : self.percent_demux_failed_score = 1 ; self.percent_demux_failed_ok = False
	
	# Percentage of tiles where demux completely failed.  Indicates problem
	# with the flowcell like dust.  Can also be caused by moving the data while
	# it's being analyzed - the threads die, the fastq 'appears' valid ( not truncated )
	# but it's missing reads..
	def setPercentTilesFailedDemux( self , percent_failed ) :
	
		self.percent_tile_demux_fail_msg = percent_failed

		if percent_failed <= self.max_percent_tile_demux_fail :
		
			self.percent_tile_demux_fail_msg   = "Average percent demux tile failure is within spec [spec: <= " + str( self.max_percent_tile_demux_fail ) + "]: " + str( "%.2f" % percent_failed )
			self.percent_tile_demux_fail_ok    = True
			self.percent_tile_demux_fail_score = 10
			self.percent_tile_demux_fail       = percent_failed
			
		else :
		
			self.percent_tile_demux_fail_msg   = "Average percent demux tile failure is greater than spec [spec: <= " + str( self.max_percent_tile_demux_fail ) + "]: " + str( "%.2f" % percent_failed )
			self.percent_tile_demux_fail_ok    = False
			self.percent_tile_demux_fail_score = 10
			self.percent_tile_demux_fail       = percent_failed

			if percent_failed > self.max_percent_tile_demux_fail         and percent_failed < self.max_percent_tile_demux_fail + 3  : self.percent_tile_demux_fail_score = 9
			elif percent_failed >= self.max_percent_tile_demux_fail + 3  and percent_failed < self.max_percent_tile_demux_fail + 7  : self.percent_tile_demux_fail_score = 8
			elif percent_failed >= self.max_percent_tile_demux_fail + 7  and percent_failed < self.max_percent_tile_demux_fail + 11 : self.percent_tile_demux_fail_score = 7
			elif percent_failed >= self.max_percent_tile_demux_fail + 11 and percent_failed < self.max_percent_tile_demux_fail + 14 : self.percent_tile_demux_fail_score = 6
			elif percent_failed >= self.max_percent_tile_demux_fail + 14 and percent_failed < self.max_percent_tile_demux_fail + 16 : self.percent_tile_demux_fail_score = 5
			elif percent_failed >= self.max_percent_tile_demux_fail + 16 and percent_failed < self.max_percent_tile_demux_fail + 18 : self.percent_tile_demux_fail_score = 4
			elif percent_failed >= self.max_percent_tile_demux_fail + 18 and percent_failed < self.max_percent_tile_demux_fail + 22 : self.percent_tile_demux_fail_score = 3
			elif percent_failed >= self.max_percent_tile_demux_fail + 22 and percent_failed < self.max_percent_tile_demux_fail + 25 : self.percent_tile_demux_fail_score = 2
			elif percent_failed >= self.max_percent_tile_demux_fail + 25 : self.percent_tile_demux_fail_score = 1	
	
	# Sometimes illumina ships half-baked and if we encounter
	# an unknown we want to warn at least
	def setMiSeqSWVersions( self , known_sw_versions_used , versions ) :
		
		if known_sw_versions_used :
			self.known_sw_versions_used_msg = "Known & tested instrument SW was used to generate fastq files"
			self.known_sw_versions_used_ok = True
			self.known_sw_versions_used_score = 10
		else :
			self.known_sw_versions_used_msg = "WARNING: Unknown & untested (by Trovagene) instrument SW was used to generate data!"
			self.known_sw_versions_used_ok = False
			self.known_sw_versions_used_score = 1
		
	# Checks that the instrument dropped the flag
	# indicating step-3 completed ( finished making fastqs )
	def setPrimaryAnalysisComplete( self , complete , step ) :
		
		if complete == True : 
			self.primary_analysis_complete_msg = "Min required step: 3 achieved: 3"
			self.primary_analysis_complete_ok = True
			self.primary_analysis_complete_score = 10
			self.last_primary_analysis_step = step
		else :
			self.primary_analysis_complete_msg = "Min required step (3) not achieved: " + str( complete )
			self.primary_analysis_complete_ok = False
			self.primary_analysis_complete_score = -1
			self.last_primary_analysis_step = step			
	
	# Sanity check to verify fastq files exist
	def setFastqFilesExist( self , exist , msg ) :

		if exist :
			self.fastq_files_exist_ok = True
			self.fastq_files_exist_msg = "All Fastq files exist"
			self.fastq_files_score = 10
		else :
			self.fastq_files_exist_ok = False
			self.fastq_files_exist_msg = msg
			self.fastq_files_score = -1
			
	# The minimum required number of clusters passed the chastity filter:
	# highest_sig_int / (highest_sig_int + 2nd_highest_sig_int) 
	# Clusters pass filter if no more than one base call in the first 25 cycles has a chastity of less than 0.6
	def setPercentPF( self , percent_pf ) :
		
		self.percent_pf = percent_pf
		
		if percent_pf >= self.min_percent_PF :
			self.percent_pf_msg = "Percent PF is within spec [spec: >= " + str( self.min_percent_PF ) + "]: " + str( "%.2f" % percent_pf )
			self.percent_pf_ok = True
			self.percent_pf_score = 10
			
		else : # somewhat sigmoidal drop is qualites as pf decreases
			
			self.percent_pf_msg = "Percent PF is less than spec [spec: >= " + str( self.min_percent_PF ) + "]: " + str( "%.2f" % percent_pf )

			if percent_pf   < self.min_percent_PF - 0.05 : self.percent_pf_score = 9
			elif percent_pf < self.min_percent_PF - 0.09 : self.percent_pf_score = 8
			elif percent_pf < self.min_percent_PF - 0.13 : self.percent_pf_score = 7
			elif percent_pf < self.min_percent_PF - 0.15 : self.percent_pf_score = 6
			elif percent_pf < self.min_percent_PF - 0.17 : self.percent_pf_score = 5
			elif percent_pf < self.min_percent_PF - 0.19 : self.percent_pf_score = 4
			elif percent_pf < self.min_percent_PF - 0.20 : self.percent_pf_score = 3
			elif percent_pf < self.min_percent_PF - 0.21 : self.percent_pf_score = 2
			elif percent_pf < self.min_percent_PF - 0.22 : self.percent_pf_score = 1
	
	# The PF cluster count should be within the density specification set by illumina for the V3 chemistry
    # Single Reads: 22-25 M
    # Paired End Reads: 44-50 M
    # For now while we are sequencing mono-template we may actually get better performance with lower density.
    # Perhaps even to the point of obtaining a very low quality score using the scale implemented.
    # A test we should add is a measure of the distance between Raw clusters and PF clusters.  If things went
    # well they should be close together - but how close?
	def setClusterCountPF( self , total_pf_clusters ) :
		
		self.total_pf_clusters = total_pf_clusters
		
		if total_pf_clusters > self.min_reads_PF and total_pf_clusters < self.max_reads_PF :
			
			self.reads_pf_msg = "The expected number of reads are available: " + str( "%.0f" % total_pf_clusters )
			self.reads_pf_ok = True
			self.reads_pf_score = 10
			
		elif total_pf_clusters > self.max_reads_PF :

				self.reads_pf_msg = "The number of reads passing filter exceeds the spec (" + str( "%.0f" % self.max_reads_PF ) + "): " + str( "%.0f" % total_pf_clusters )
				self.reads_pf_ok = True
				
				if total_pf_clusters    > self.max_reads_PF + 1000000 and total_pf_clusters < self.max_reads_PF + 1500000 : self.reads_pf_score = 9 
				elif total_pf_clusters >= self.max_reads_PF + 1500000 and total_pf_clusters < self.max_reads_PF + 2000000 : self.reads_pf_score = 8 
				elif total_pf_clusters >= self.max_reads_PF + 2000000 and total_pf_clusters < self.max_reads_PF + 2500000 : self.reads_pf_score = 7 
				elif total_pf_clusters >= self.max_reads_PF + 2500000 and total_pf_clusters < self.max_reads_PF + 3000000 : self.reads_pf_score = 6 
				elif total_pf_clusters >= self.max_reads_PF + 3000000 and total_pf_clusters < self.max_reads_PF + 3500000 : self.reads_pf_score = 5 
				elif total_pf_clusters >= self.max_reads_PF + 3500000 and total_pf_clusters < self.max_reads_PF + 4000000 : self.reads_pf_score = 4 
				elif total_pf_clusters >= self.max_reads_PF + 4000000 and total_pf_clusters < self.max_reads_PF + 4500000 : self.reads_pf_score = 3 
				elif total_pf_clusters >= self.max_reads_PF + 4500000 and total_pf_clusters < self.max_reads_PF + 5000000 : self.reads_pf_score = 2 
				elif total_pf_clusters >= self.max_reads_PF + 5000000                                                     : self.reads_pf_score = 1 
				
		elif total_pf_clusters < self.min_reads_PF :

				self.reads_pf_msg = "The number of reads passing filter does not meet spec (" + str( "%.0f" % self.min_reads_PF ) + "): " + str( "%.0f" % total_pf_clusters )
				
				if   total_pf_clusters > self.min_reads_PF - 2000000  : self.reads_pf_score = 9 ; self.reads_pf_ok = True
				elif total_pf_clusters > self.min_reads_PF - 4000000  : self.reads_pf_score = 8 ; self.reads_pf_ok = True
				elif total_pf_clusters > self.min_reads_PF - 8000000  : self.reads_pf_score = 7 ; self.reads_pf_ok = True
				elif total_pf_clusters > self.min_reads_PF - 10000000 : self.reads_pf_score = 6 ; self.reads_pf_ok = True
				elif total_pf_clusters > self.min_reads_PF - 12000000 : self.reads_pf_score = 5
				elif total_pf_clusters > self.min_reads_PF - 14000000 : self.reads_pf_score = 4
				elif total_pf_clusters > self.min_reads_PF - 16000000 : self.reads_pf_score = 3
				elif total_pf_clusters > self.min_reads_PF - 17000000 : self.reads_pf_score = 2
				elif total_pf_clusters > 9000000                      : self.reads_pf_score = 1
   
	# Sets the percentage of PhiX which aligned.  Currently we are spiking in 5% and so we'd expect to see 5% aligned.
	# If not it may be due to:
	# 1. PhiX sample degradation - a tube freeze/thawed multiple times over a week of use may degrade so that even though
	#    the lab thinks they are spiking in 5% it is now 2%. Recommend aliquot and store single use tubes.
	# 2. Can also indicate overall poor sequencing quality if the error (1) is avoided.
	def setPercentPhiXAligned( self , average_phix_aligned ) :
		
		self.average_phix_aligned = average_phix_aligned
		
		if average_phix_aligned >= self.min_percent_phix_aligned :
			
			self.percent_phix_aligned_msg = "Percent PhiX Aligned is within spec [spec: >= " + \
			str( "%.2f" % self.min_percent_phix_aligned ) + "]: " + str( "%.2f" % average_phix_aligned )

			# Too much PHIX indicates low to no human
			if average_phix_aligned < self.max_percent_phix_aligned :
				self.percent_phix_aligned_ok = True
				self.percent_phix_aligned_score = 10
			else :
				self.percent_phix_aligned_ok = False
				self.percent_phix_aligned_score = 1				
				self.percent_phix_aligned_msg = "Percent PhiX Aligned indicates overloading PhiX or underloading Human: " + str( "%.2f" % average_phix_aligned )
		else :
		
			self.percent_phix_aligned_msg = "Percent PhiX Aligned is less than spec [spec: " + \
			str( "%.2f" %  self.min_percent_phix_aligned ) + "]: " + str( "%.2f" % average_phix_aligned )
			
			if   average_phix_aligned < self.min_percent_phix_aligned and average_phix_aligned >= self.min_percent_phix_aligned - 0.5 :       self.percent_phix_aligned_score = 9 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 0.5 and average_phix_aligned >= self.min_percent_phix_aligned - 1 :   self.percent_phix_aligned_score = 8 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 1   and average_phix_aligned >= self.min_percent_phix_aligned - 1.5 : self.percent_phix_aligned_score = 7 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 1.5 and average_phix_aligned >= self.min_percent_phix_aligned - 2 :   self.percent_phix_aligned_score = 6 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 2   and average_phix_aligned >= self.min_percent_phix_aligned - 2.5 : self.percent_phix_aligned_score = 5 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 2.5 and average_phix_aligned >= self.min_percent_phix_aligned - 3 :   self.percent_phix_aligned_score = 4 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 3   and average_phix_aligned >= self.min_percent_phix_aligned - 3.5 : self.percent_phix_aligned_score = 3 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 3.5 and average_phix_aligned >= self.min_percent_phix_aligned - 4 :   self.percent_phix_aligned_score = 2 ; self.percent_phix_aligned_ok = True
			elif average_phix_aligned < self.min_percent_phix_aligned - 4 :                                                                   self.percent_phix_aligned_score = 1 ; self.percent_phix_aligned_ok = True
		
	# Sets the Prephasing applied status: Correction for % of DNA strands per cluster which
	# have erroneously fallen ahead of the current cycle by one or more bases 
	def setPrephasingApplied( self , average_prephasing ) :
	
		self.average_prephasing = average_prephasing
		
		if average_prephasing <= self.max_prephasing :
		
			self.prephasing_score = 10
			self.prephasing_msg = "Prephasing applied is within spec [spec: <= " + str( "%.2f" % self.max_prephasing ) + "]: " + str( "%.2f" % average_prephasing ) 
			self.prephasing_ok = True
		
		else : # primitive quality score for now...
			
			difference = average_prephasing - self.max_prephasing

			if difference < 0.1 : self.prephasing_score = 9
			elif difference >= 0.1 and difference <= 0.2 : self.prephasing_score = 8
			elif difference > 0.2 and difference <= 0.3 : self.prephasing_score = 7
			elif difference > 0.3 and difference <= 0.4 : self.prephasing_score = 6
			elif difference > 0.4 and difference <= 0.5 : self.prephasing_score = 5
			elif difference > 0.5 and difference <= 0.6 : self.prephasing_score = 4
			elif difference > 0.6 and difference <= 0.7 : self.prephasing_score = 3
			elif difference > 0.7 and difference <= 0.8 : self.prephasing_score = 2
			elif difference > 0.8 : self.prephasing_score = 1

			self.prephasing_msg = "Prephasing applied is greater than spec [spec: <= " + str( "%.2f" % self.max_prephasing ) + "]: " + \
			str( "%.2f" % average_prephasing ) + ". Difference is: " + str( "%.2f" % difference )		
		
	# Sets the Phasing applied status: Correction for % of DNA strands per cluster which
	# have erroneously fallen behind the current cycle by one or more bases 
	def setPhasingApplied( self , average_phasing ) :
	
		self.average_phasing = average_phasing
		
		if average_phasing <= self.max_phasing :
		
			self.phasing_score = 10
			self.phasing_msg = "Phasing applied is within spec [spec: <= " + str( "%.2f" % self.max_phasing ) + "]: " + str( "%.2f" % average_phasing ) 
			self.phasing_ok = True
		
		else : # primitive quality score for now...
			
			difference = average_phasing - self.max_phasing

			if difference < 0.1 : self.phasing_score = 9
			elif difference >= 0.1 and difference <= 0.2 : self.phasing_score = 8
			elif difference > 0.2 and difference <= 0.3 : self.phasing_score = 7
			elif difference > 0.3 and difference <= 0.4 : self.phasing_score = 6
			elif difference > 0.4 and difference <= 0.5 : self.phasing_score = 5
			elif difference > 0.5 and difference <= 0.6 : self.phasing_score = 4
			elif difference > 0.6 and difference <= 0.7 : self.phasing_score = 3
			elif difference > 0.7 and difference <= 0.8 : self.phasing_score = 2
			elif difference > 0.8 : self.phasing_score = 1

			self.phasing_msg = "Phasing applied is greater than spec [spec: <= " + str( "%.2f" % self.max_phasing ) + "]: " + \
			str( "%.2f" % average_phasing ) + ". Difference is: " + str( "%.2f" % difference )	
		
	# One of the most important metrics relating run quality.  
	# More important that it's not too dense (over-cooked) rather than not dense enough (undercooked)
	# For now while we are sequencing mono-template we may actually get better performance with lower density.
	# Perhaps even to the point of obtaining a very low quality score using the scale implemented.
    # A test we should add is a measure of the distance between Raw clusters and PF clusters.  If things went
    # well they should be close together - but how close?
	def setAverageDensity( self , average_density ) :
		
		self.cluster_density = average_density
		
		if average_density <= self.max_cluster_density and average_density >= self.min_cluster_density :
			
			self.cluster_density_msg = "Raw cluster density is within spec [spec: >= " + str( int( self.min_cluster_density / 1000 ) ) + "K/mm^2 and <= " + \
			str( int( self.max_cluster_density / 1000 ) ) + "K/mm^2]: " + str( int( average_density / 1000 ) ) + "K/mm^2"
			
			self.cluster_density_ok = True
			self.cluster_density_score = 10
			
		else :
			
			if average_density < self.min_cluster_density : # undercooked, better than overcooked
				percent_difference = abs( self.min_cluster_density - average_density ) / abs( ( self.min_cluster_density + average_density ) / 2 ) * 100
				if percent_difference < 15 : self.cluster_density_score = 9
				elif percent_difference >= 15 and percent_difference < 35   : self.cluster_density_score = 8
				elif percent_difference >= 35 and percent_difference < 50   : self.cluster_density_score = 7
				elif percent_difference >= 50 and percent_difference < 65   : self.cluster_density_score = 6
				elif percent_difference >= 65 and percent_difference < 80   : self.cluster_density_score = 5
				elif percent_difference >= 80 and percent_difference < 95   : self.cluster_density_score = 4
				elif percent_difference >= 95 and percent_difference < 110  : self.cluster_density_score = 3
				elif percent_difference >= 110 and percent_difference < 125 : self.cluster_density_score = 2
				elif percent_difference >= 125 : self.cluster_density_score = 1
			
			elif average_density > self.max_cluster_density :
				percent_difference = abs( self.max_cluster_density - average_density ) / abs( ( self.max_cluster_density + average_density ) / 2 ) * 100
				if percent_difference < 1 : self.cluster_density_score = 9
				elif percent_difference >= 1 and percent_difference < 5   : self.cluster_density_score = 8
				elif percent_difference >= 5 and percent_difference < 10  : self.cluster_density_score = 7
				elif percent_difference >= 10 and percent_difference < 15 : self.cluster_density_score = 6
				elif percent_difference >= 15 and percent_difference < 20 : self.cluster_density_score = 5
				elif percent_difference >= 20 and percent_difference < 25 : self.cluster_density_score = 4
				elif percent_difference >= 25 and percent_difference < 30 : self.cluster_density_score = 3
				elif percent_difference >= 30 and percent_difference < 35 : self.cluster_density_score = 2
				elif percent_difference >= 35 : self.cluster_density_score = 1
		
			self.cluster_density_msg = "Raw cluster density is not within spec [spec: >= " + str( "%.0f" % ( self.min_cluster_density / 1000 ) ) + "K/mm^2 and <= " + \
                str( "%.0f" % ( self.max_cluster_density  / 1000 ) ) + "K/mm^2]: " + str( "%.0f" % ( average_density / 1000 ) )  + \
				" K/mm^2. Percent Difference is: " + str( "%.0f" % ( percent_difference ) )

		# This is density for data which has passed the chastity filter.  The raw density
		# is more informative but it's not always estimated correctly by the illumina
		# software.  PF density should be lower but relatively close if the true
		# density is in the sweet spot of the illumina image analysis algorithms.
		# For now while we are sequencing mono-template we may actually get better performance with lower density.
		# Perhaps even to the point of obtaining a very low quality score using the scale implemented.
		# A test we should add is a measure of the distance between Raw clusters and PF clusters.  If things went
		# well they should be close together - but how close?			
	def setAverageDensityPF( self , average_density_pf ) :
	
		self.cluster_density_pf = average_density_pf
		
		if average_density_pf <= self.max_cluster_density and average_density_pf >= self.min_cluster_density :
			
			self.cluster_density_pf_msg = "PF cluster density is within spec [spec: >= " + str( int( self.min_cluster_density / 1000 ) ) + "K/mm^2 and <= " + \
			str( int( self.max_cluster_density / 1000 ) ) + "K/mm^2]: " + str( int( average_density_pf / 1000 ) ) + "K/mm^2"
			
			self.cluster_density_pf_ok = True
			self.cluster_density_pf_score = 10
	
		else :
			
			if average_density_pf < self.min_cluster_density : # undercooked, better than overcooked
				percent_difference = abs( self.min_cluster_density - average_density_pf ) / abs( ( self.min_cluster_density + average_density_pf ) / 2 ) * 100
				if percent_difference < 15 : self.cluster_density_pf_score = 9
				elif percent_difference >= 15 and percent_difference < 35   : self.cluster_density_pf_score = 8
				elif percent_difference >= 35 and percent_difference < 50   : self.cluster_density_pf_score = 7
				elif percent_difference >= 50 and percent_difference < 65   : self.cluster_density_pf_score = 6
				elif percent_difference >= 65 and percent_difference < 80   : self.cluster_density_pf_score = 5
				elif percent_difference >= 80 and percent_difference < 95   : self.cluster_density_pf_score = 4
				elif percent_difference >= 95 and percent_difference < 110  : self.cluster_density_pf_score = 3
				elif percent_difference >= 110 and percent_difference < 125 : self.cluster_density_pf_score = 2
				elif percent_difference >= 125 : self.cluster_density_pf_score = 1
			
			elif average_density_pf > self.max_cluster_density :
				percent_difference = abs( self.max_cluster_density - average_density_pf ) / abs( ( self.max_cluster_density + average_density_pf ) / 2 ) * 100
				if percent_difference < 1 : self.cluster_density_pf_score = 9
				elif percent_difference >= 1 and percent_difference < 5   : self.cluster_density_pf_score = 8
				elif percent_difference >= 5 and percent_difference < 10  : self.cluster_density_pf_score = 7
				elif percent_difference >= 10 and percent_difference < 15 : self.cluster_density_pf_score = 6
				elif percent_difference >= 15 and percent_difference < 20 : self.cluster_density_pf_score = 5
				elif percent_difference >= 20 and percent_difference < 25 : self.cluster_density_pf_score = 4
				elif percent_difference >= 25 and percent_difference < 30 : self.cluster_density_pf_score = 3
				elif percent_difference >= 30 and percent_difference < 35 : self.cluster_density_pf_score = 2
				elif percent_difference >= 35 : self.cluster_density_pf_score = 1
		
			self.cluster_density_pf_msg = "PF cluster density is not within spec [spec: >= " + str( "%.0f" % ( self.min_cluster_density / 1000 ) ) + "K/mm^2 and <= " + \
                str( "%.0f" % ( self.max_cluster_density / 1000 ) ) + "K/mm^2]: " + str( "%.0f" % ( average_density_pf / 1000 ) )  + \
				" K/mm^2. Percent Difference is: " + str( "%.0f" % ( percent_difference ) )
	
	# Failure of any of these results in a "No" answer to the
	# question: "Is this data good enough for teriary analysis?"
	# Secondary analysis being fastq file generation via MiSeq Reporter
	def OK( self ) :
		if self.fastq_files_exist_ok and self.primary_analysis_complete_ok and self.average_phix_error_rate_ok and \
		   self.known_sw_versions_used_ok and self.reads_pf_ok and self.percent_phix_aligned_ok and \
		   self.percent_demux_failed_ok and self.percent_tile_demux_fail_ok : return True , "AOK"
		elif not self.fastq_files_exist_ok :
			return False , self.fastq_files_exist_msg
		elif not self.primary_analysis_complete_ok :
			return False , self.primary_analysis_complete_msg
		elif not self.average_phix_error_rate_ok :
			return False , self.average_phix_error_rate_msg
		elif not self.known_sw_versions_used_ok :
			return False , self.known_sw_versions_used_msg
		elif not self.reads_pf_ok :
			return False , self.reads_pf_msg
		elif not self.percent_phix_aligned_ok :
			return False , self.percent_phix_aligned_msg
		elif not self.percent_demux_failed_ok :
			return False , self.percent_demux_failed_msg
		elif not self.percent_tile_demux_fail_ok :
			return False , self.percent_tile_demux_fail_msg
	
	####################################
	# MAIN INITIALIZATION

	def __init__( self , config ):
				
		self.average_phix_aligned    = 0
		self.total_pf_clusters       = 0
		self.percent_pf              = 0
		self.average_prephasing      = 0
		self.average_phasing         = 0
		self.cluster_density         = 0
		self.cluster_density_pf      = 0
		self.average_demux_failed    = 0
		self.average_phix_error_rate = 0
		self.percent_tile_demux_fail = 0
		
		self.cluster_density_msg           = "File not found"
		self.cluster_density_pf_msg        = "File not found"
		self.phasing_msg                   = "File not found"
		self.prephasing_msg                = "File not found"
		self.percent_phix_aligned_msg      = "File not found"
		self.cluster_count_pf_msg          = "File not found"
		self.percent_pf_msg                = "File not found"
		self.reads_pf_msg                  = "File not found"
		self.fastq_files_exist_msg         = "File not found"
		self.primary_analysis_complete_msg = "File not found"
		self.known_sw_versions_used_msg    = "File not found"
		self.percent_demux_failed_msg      = "File not found"
		self.average_phix_error_rate_msg   = "File not found"
		self.percent_tile_demux_fail_msg   = "File not found"
		
		self.cluster_density_ok           = False
		self.cluster_density_pf_ok        = False
		self.phasing_ok                   = False
		self.prephasing_ok                = False
		self.percent_phix_aligned_ok      = False
		self.reads_pf_ok                  = False
		self.percent_pf_ok                = False
		self.fastq_files_exist_ok         = False
		self.primary_analysis_complete_ok = False
		self.known_sw_versions_used_ok    = False
		self.percent_demux_failed_ok      = False
		self.average_phix_error_rate_ok   = False
		self.percent_tile_demux_fail_ok   = False
		
		self.cluster_density_score           = 0
		self.cluster_density_pf_score        = 0
		self.phasing_score                   = 0
		self.prephasing_score                = 0
		self.percent_phix_aligned_score      = 0
		self.reads_pf_score                  = 0
		self.percent_pf_score                = 0
		self.fastq_files_score               = 0
		self.primary_analysis_complete_score = 0
		self.known_sw_versions_used_score    = 0
		self.percent_demux_failed_score      = 0
		self.average_phix_error_rate_score   = 0
		self.percent_tile_demux_fail_score   = 0
		
		self.last_primary_analysis_step = 3    # an illumina workflow step, last step in GenerateFASTQ workflow
		self.min_reads_PF = 17500000           # based on cluster density for v3 chemistry:(1200-1400 K/m) diverse or 500-1200 K/m monotemplate PF.  For diverse: 22000000
		self.max_reads_PF = 22000000           # based on cluster density for v3 chemsitry: (1200-1400 K/m diverse or 500-1200 K/m monotemplate PF ) For diverse: 25000000 
		self.min_percent_phix_aligned = 5      # currently spiking in 5% but more is better for mono-template. Lower score if degrades. 
		self.max_percent_phix_aligned = 60     # indicates at most only 40% of the flowcell is human, which is not good
		self.min_percent_PF = 75               # not too conservative considering monotemplate
		self.max_error_rate = 0.50             # Control PhiX RTA/SeqAn alignment error rate
		self.max_phasing = 0.5                 # percent of clusters falling behind (ideal is < 0.25)
		self.max_prephasing = 0.3              # percent clusters getting ahead (ideal is < 0.15)
		self.max_cluster_density = 1200000     # MiSeq v3 reagents accommodate an optimal raw cluster density of ( 1200-1400 K/m diverse or 500-1200 K/m monotemplate )
		self.min_cluster_density = 500000      # MiSeq v3 reagents accommodate an optimal raw cluster density of ( 1200-1400 K/m diverse or 500-1200 K/m monotemplate )
		self.max_mean_demux_failure = 20       # 5-10% is considered good, this is liberal because we're sequencing mono-template
		self.max_percent_tile_demux_fail = 10  # Percentage of tiles were zero reads demultiplex
					
		self.VerifyFastqFilesExist( config )
		self.VerifyPrimaryAnalysisComplete( config )
		self.VerifyIlluminaSoftwareVersions( config )
		self.EvaluateTileMetrics( config )
		self.CalculatePercentFailedDemux( config )
		self.CalculatePercentTileDemuxFail( config )
		self.EvaluateErrorMetrics( config )
			

				
