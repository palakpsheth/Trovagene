#!/usr/bin/env python
from __future__ import division
import sys
import os
import struct

class TileMetrics :

	def __init__( self , tile_metrics_file ):
				
		self.total_raw_clusters = 0
		self.total_pf_clusters  = 0
		self.cluster_density    = list()
		self.cluster_density_PF = list()
		self.phasing    = {}
		self.prephasing = {}
		self.percentPhixAligned = {}
		
		self.average_density      = 0
		self.average_density_pf   = 0 
		self.average_phasing      = 0
		self.average_prephasing   = 0
		self.average_phix_aligned = 0
		
		filesize = 0
		position = 0
	
		with open( tile_metrics_file, 'rb' ) as f :
			data = f.read()
			filesize = len( data )
		
		with open( tile_metrics_file, 'rb' ) as f :
			
			file_version = f.read(1)
			record_length = f.read(1)
			position += 2
		
			while position < filesize :
				
				bytes = f.read(2);
				lane_number = struct.unpack('BB', bytes[0:2])[0] # unpack 2 bytes to int16, if it were int 8 it would be 'B', bytes[0]
				position += 2;

				bytes = f.read(2);
				tile = struct.unpack('H', bytes[0:2])[0] 
				position += 2;

				bytes = f.read(2);
				metric_code = struct.unpack('H', bytes[0:2])[0] 
				position += 2;

				bytes = f.read(4);
				metric_value = struct.unpack('f', bytes[0:4])[0] 
				position += 4;
				
				self.appendMetric(tile, metric_code, metric_value)
	
			if len( self.cluster_density ) != 0 :
				self.average_density    = reduce( lambda x, y: x + y, self.cluster_density ) / len( self.cluster_density )
			else : self.average_density = -1
			if len( self.cluster_density_PF ) != 0 :
				self.average_density_pf = reduce( lambda x, y: x + y, self.cluster_density_PF ) / len( self.cluster_density_PF )
			else : self.average_density_pf = -1
			if len( self.phasing.values() ) != 0 :
				self.average_phasing    = reduce( lambda x, y: x + y, self.phasing.values() ) / len( self.phasing.values() ) * 100
			else : self.average_phasing = float( "Inf" )
			if len( self.prephasing.values() ) != 0 :
				self.average_prephasing = reduce( lambda x, y: x + y, self.prephasing.values() ) / len( self.prephasing.values() ) * 100
			else : self.average_prephasing = float( "Inf" )
			if len( self.percentPhixAligned.values() ) != 0 :
				self.average_phix_aligned = reduce( lambda x, y: x + y, self.percentPhixAligned.values() ) / len( self.percentPhixAligned.values() )
			else : self.average_phix_aligned = float( "-Inf" )
			
	# Percent of reads which passed the chastity filter
	def Get_Percent_PF( self ) :
		if self.total_raw_clusters == 0 : return 0
		return ( self.total_pf_clusters / self.total_raw_clusters ) * 100;	
	
	# Save the last value seen and over-write intermediates
	def Set_Phasing( self , tile , metric_value ) :
		self.phasing[ tile ] = metric_value
		
	# Save the last value seen and over-write intermediates
	def Set_Prephasing( self , tile , metric_value ) :
		self.prephasing[ tile ] = metric_value
		
	# Save the last value seen and over-write intermediates		
	def Set_Percent_Phix_Aligned( self, tile , metric_value ) :
		self.percentPhixAligned[ tile ] = metric_value

	# Taken from a switch/case in my C# code
	def appendMetric( self, tile, metric_code, metric_value ) :

		if metric_code   == 100 : # cluster density
			self.cluster_density.append( metric_value )
		elif metric_code == 101 : # cluster density passing filters
			self.cluster_density_PF.append( metric_value )
		elif metric_code == 102 : # number of clusters
			self.total_raw_clusters += metric_value 
		elif metric_code == 103 : # number of clusters passing filters
			self.total_pf_clusters += metric_value
		elif metric_code == 200 : # phasing
			self.Set_Phasing( tile , metric_value )
		elif metric_code == 201 : # prephasing
			self.Set_Prephasing( tile , metric_value )
		elif metric_code == 300 : # percent aligned (RTA+Seqan)
			self.Set_Percent_Phix_Aligned( tile , metric_value )
		# elif metric_code == 400 : # control lane
			# ignored
			
			