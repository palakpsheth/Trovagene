import sys, os

class DataAnalysisWrapperError(Exception):
	pass

class UnknownOSError(Exception):
	em = {1001: 'Unknown operating system.  Please run on Windows, Mac OSX, or Linux.  Exiting...'}

class OptionError(Exception):
	em = {1101: 'Unknown option.  See above for usage details.  Exiting...',
		  1102: 'Missing --input_dir (-i) option.  See above for usage details.  Exiting...',
		  1103: 'input_dir is incorrectly specified.  Needs to end in "' + os.path.join('...','<runid>','Data','Intensities','BaseCalls','') + '".  Exiting...',
		  1104: 'Run ID inferred from input_dir is not of the correct format.  Exiting...',
		  1105: 'Missing --config_file (-c) option.  See above for usage details.  Exiting...'}

class PathError(Exception):
	em = {1201: 'Path specified by --pipeline_path (-p) does not exist.  Exiting...',
		  1202: 'Path specified by --basecalls_dir (-i) does not exist.  Exiting...',
		  1203: 'Path specified by --results_dir (-u) does not exist.  Exiting...',
		  1204: 'Path specified by --outfiles_dir (-a) does not exist.  Exiting...',
		  1205: 'Path specified by --cache_dir (-z) does not exist.  Exiting...',
		  1206: 'Path specified by --raw_outfile (-w) does not exist.  Exiting...',
		  1207: 'Path specified by --csv_outfile (-o) does not exist.  Exiting...',
		  1208: 'Path specified by --db_outfile (-d) does not exist.  Exiting...',
		  1209: 'Path specified by --stats_outfile (-t) does not exist.  Exiting...',
		  1210: 'Path specified by --ss_outfile (-v) does not exist.  Exiting...',
		  1211: 'Path specified by --csv_cache (-c) does not exist.  Exiting...',
		  1212: 'Path specified by --sample_sheet (-s) does not exist.  Exiting...',
		  1213: 'SampleSheet.csv not found in root run folder. Exiting...',
		  1214: 'Run specific directory within specified working directory already exists. Use --force to overwrite. Exiting...'}

class SSValidatorError(Exception):
	em = {1301: 'There are multiple rows with "[Data]" in first column (should be only one). Exiting...',
		  1302: 'There are no rows with "[Data]" in first column (should be only one).  Exiting...',
		  1303: 'Sample sheet does not have "Sample_ID" column.  Exiting...',
		  1304: 'Sample sheet does not have "Sample_Name" column.  Exiting...',
		  1305: 'Sample sheet does not have "Sample_Project" column.  Exiting...',
		  1306: 'Sample sheet does not have "Source" column.  Exiting...',
		  1307: 'Sample sheet does not have "Input" column.  Exiting...',
		  1308: 'Problem matching FastQ files.  Exiting...',
		  1309: 'Sample sheet Sample_ID is out of order (needs to be sequential integers).  Exiting...',
		  1310: 'Exactly 3 replicates not found for all samples labeled as "Standard". At least one standard level was not run in triplicate.  Exiting...',
		  1311: 'At least one sample does not have a valid associated standard curve for the Assay/Source/Input/Standard_Group combination.  Exiting...',
		  1312: 'Sample sheet does not have "Standard_Group" column.  Exiting...',
		  1313: 'Sample sheet does not have "Batch" column.  Exiting...',
		  1314: 'Sample sheet does not have "Checkout_Number" column.  Exiting...',
		  1315: 'Sample sheet does not have "Ng_Per_Rxn" column.  Exiting...',
		  1316: 'Sample sheet does not have "Phix_Fraction" column.  Exiting...',
		  1317: 'Sample sheet does not have "Project_Version" column.  Exiting...',
		  1318: 'Validated sample sheet not found! Check log files for details. Exiting...',
		  1319: 'Not all rows have int type "Sample_ID" value. Exiting...',
		  1320: 'Not all rows have string type "Sample_Name" value. Exiting...',
		  1321: '"Sample_ID" numbering issue found. "Sample_ID" column numbering must start with "1" and continue sequentially. Possible non-sequential "Sample_ID" names found. Exiting...',
		  1322: 'Invalid "Sample_Name" name(s) found. Non-alphanumeric characters including spaces are invalid. Exiting...',
		  1323: 'Sample sheet does not have "Sample_Plate" column.  Exiting...',
		  1324: 'Sample sheet does not have "Sample_Well" column.  Exiting...',
		  1325: 'Not all rows have string type "Sample_Plate" value. Exiting...',
		  1326: 'Not all rows have string type "Sample_Well" value. Exiting...',
		  1327: 'Sample sheet does not have "I7_Index_ID" column.  Exiting...',
		  1328: 'Sample sheet does not have "Index" column.  Exiting...',
		  1329: 'Not all rows have string type "Index" value. Exiting...',
		  1330: 'Not all rows have string type "Sample_Project" value. Exiting...',
		  1331: 'Not all rows have a valid "Sample_Project" value. Unrecognized assay found. Exiting...',
		  1332: 'Sample sheet does not have "Description" column.  Exiting...',
		  1333: 'Not all rows have string type "Description" value. Exiting...',
		  1334: 'Not all rows have string type "Source" value. Exiting...',
		  1335: 'Not all rows have float type "Ng_Per_Rxn" value. Exiting...',
		  1336: 'Not all rows have float type "Phix_Fraction" value. Exiting...',
		  1337: 'Not all rows have string type "Batch" value. Exiting...',
		  1338: 'Not all rows have int type "Checkout_Number" value. Exiting...',
		  1339: 'Not all rows have int type "Project_Version" value. Exiting...',
		  1340: 'Not all rows have float type "Input" value. Exiting...',
		  1341: 'Not all rows have int type "Standard_Group" value. Exiting...',
		  1342: 'Did not find at least 4 standard curve levels per standard group. Exiting...',
		  1343: 'Potential mismatch in "Standard_Group" column based on the Assay/Source/Input combinations.  Exiting...',}

class PipelineError(Exception):
	em = {1401: 'Error when running pipeline. Exiting...'}
	
class ConfigFileError(Exception):
	em = {1501: 'Config file missing required fields under [global]. Exiting...'}

class SequencingQcError(Exception):
	em = {1601: 'Sequencing QC failed. Exiting...',
		  1602: '_stats.csv file not found! Check log files for details. Exiting...'}

class ReadsProcessingError(Exception):
	em = {1701: 'Reads processing error. See log files. Exiting...',
		  1702: '_RAWCOUNTS.csv file not found! Check log files for details. Exiting...'}

class DataAnalysisError(Exception):
	em = {1801: 'Data analysis error. See log files. Exiting...',
		  1802: '_summary.csv file not found! Check log files for details. Exiting...',
		  1803: '_all_plots.pdf file not found! Check log files for details. Exiting...'}

class OutputFormatterError(Exception):
	em = {1901: 'Output formatter error. See log files. Exiting...',
		  1902: 'Unable to format "Metric" column. Exiting...',
		  1903: 'Unable to remap "_summary.csv" file column names. Possible missing column in unformatted "_summary" file. Exiting...',
		  1904: 'Unequal number of columns in unformatted "_summary.csv" and column name remapping file. Possible missing column in unformatted "_summary" file. Exiting...',}
