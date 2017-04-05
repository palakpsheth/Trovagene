<html style="margin-left: 10px">
<?php
	// find config file
	$files = glob("../config.ini");
	// load config file
	$sections = parse_ini_file( $files[0], true, INI_SCANNER_RAW );
	// create a list of keys
	$keys = array_keys($sections);
	
	// loop over each key and print each section's info
	foreach( $keys as $key ) {
		
		if ( preg_match('/(readsProcessing)/i', $key) ){
			continue;
		}
		
		echo '<table border=1 style="width:500px;font-size:12px;font-size:14px">';
		//echo '<col width="25%">';
		//echo '<col width="25%">';
		echo '<tr ><th colspan="3" style="font-size:14px" align="right">'.$key.' Parameters</th></tr>';
		$section = $sections[$key];
		$section_keys = array_keys($section);
		$count = 0;
		
		# first echo important global options
		if ( preg_match('/(global)/i', $key) ){
			foreach( $section_keys as $section_key ) {
				if ( preg_match('/(workingDir|outputDir)/i', $section_key) ){
					echo '<tr><td width="50%">'.$section_key.' </td><td> '.$section[$section_key].'</td></tr>';
					$count = $count + 1;
				}
			}
		}
		# second echo important readsprocessing [skip]
		
		# third echo imp. data analysis
		elseif ( preg_match('/(dataanalysis)/i', $key) ){
			foreach( $section_keys as $section_key ) {
				if ( preg_match('/(ntc_maxreads)/i', $section_key) ){
					echo '<tr><td width="50%">'.$section_key.' </td><td> '.$section[$section_key].'</td></tr>';
					$count = $count + 1;
				}
			}
		}
		
		# else echo others
		else {
			foreach( $section_keys as $section_key ) {
				if ( preg_match('/(reads_qc_col|minreads|threshold|demux|lloq)/i', $section_key) ){
					echo '<tr><td width="50%">'.$section_key.' </td><td> '.$section[$section_key].'</td></tr>';
					$count = $count + 1;
				}
			}
		}
		
		if ($count == 0) {
			echo '<tr><td width="50%">DATA ANALYSIS PARAMETERS</td><td>UNDEFINED</td></tr>';
		}
		
		echo '</table>';
		echo '<br>';
	}
	
	
	
	
	
	
	
	
?>
</html>
