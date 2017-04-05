#!/usr/bin/env python
from __future__ import division
import sys
import os
import struct

class ErrorMetrics :

	def __init__( self , error_metrics_file ):

		self.average_error_rate = 0
		
		filesize = 0
		position = 0
	
		with open( error_metrics_file , 'rb' ) as f :
			data = f.read()
			filesize = len( data )
		
		with open( error_metrics_file , 'rb' ) as f :
			
			file_version = f.read(1)
			record_length = f.read(1)
			position += 2
			
			error_rate_list = list()
		
			while position < filesize :
				
				bytes = f.read(2)
				lane_number = struct.unpack('BB', bytes[0:2])[0] # unpack 2 bytes to int16, if it were int 8 it would be 'B', bytes[0]
				position += 2

				bytes = f.read(2)
				tile = struct.unpack('H', bytes[0:2])[0] 
				position += 2

				bytes = f.read(2)
				cycle = struct.unpack('H', bytes[0:2])[0] 
				position += 2

				bytes = f.read(4);
				error_rate = struct.unpack('f', bytes[0:4])[0] 
				position += 4
				
				bytes = f.read(4);
				number_of_perfect_reads = struct.unpack('i', bytes[0:4])[0] 
				position += 4
				
				bytes = f.read(4);
				number_of_reads_with_one_error = struct.unpack('i', bytes[0:4])[0] 
				position += 4
				
				bytes = f.read(4);
				number_of_reads_with_two_errors = struct.unpack('i', bytes[0:4])[0] 
				position += 4
				
				bytes = f.read(4);
				number_of_reads_with_three_errors = struct.unpack('i', bytes[0:4])[0] 
				position += 4
				
				bytes = f.read(4);
				number_of_reads_with_four_errors = struct.unpack('i', bytes[0:4])[0] 
				position += 4
				
				error_rate_list.append( error_rate )
				
			self.average_error_rate = reduce( lambda x, y: x + y, error_rate_list ) / len( error_rate_list )
			
			
		
			
			