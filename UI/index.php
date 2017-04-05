<html style="margin-left: 10px">
  <head>
    <?php include 'include/site.php'?>
    <title><?php echo $INSTANCE ?> NGS Analysis Tools</title>
    <link href="styles/bootstrap.css" rel="stylesheet">
    <!-- Vermilion Theme -->
    <link href="styles/vermilion-theme.css" rel="stylesheet">
    <!--<link type="text/css" href="../styles/trovapipe.css" rel="stylesheet">-->
  </head>
  <body  bgcolor="#EFEFFA">
       <?php
                $load = sys_getloadavg();
                if ($load[0] > 10000) {
					//header('HTTP/1.1 503 Too busy, try again later');
					//die('Server too busy. Please try again later.');
                }
        ?>

    <?php include 'include/menu.php'?>

   <!-- <h2><?php echo $STATUS ?>: <?php echo $INSTANCE ?> Analysis Tools</h2> -->
   <h2><?php echo $INSTANCE ?> <?php echo $STATUS ?> Analysis Tools</h2>
   <h3>TrovaPipe <?php echo $MAJOR ?> 
	<?php 
		echo "Using Trovagene SGE Cluster";
	?>	
    </h3>
<!--
    <h3><mark><?php echo $INSTANCE ?> <?php echo $Run_type ?> site is a preview of the QA site </mark></h3> 
-->

    <form action="" method="post">
	
	<h3><b>Select run repository:</b></h3>
	<select onchange="this.form.submit()" required="required" name="runrepo" id="runrepo" style="font-weight: bold; margin-left: 25px" >
	<?php
		#if (isset($_POST['runrepo']) && !isset($_POST['button'])) {
		#	unset($_POST['rundir']);
		#}
		echo '<option >-----SELECT REPO HERE-----</option>';
		foreach($runs_repo as $repo)
		{
			if ($_POST['runrepo'] == $repo) {
				echo '<option selected="selected" value="'.$repo.'" >' . $repo . '</option>';
				//break;
			}
			else {
				if (is_dir("$repo") and $repo[0]!=='.' and $repo !== 'archive' and $repo !== 'Archive')
				{
					echo '<option value="'.$repo.'" >' . $repo . '</option>';
				}
			}
		}
	?>
    </select>
    <br>
    <br>
    <h3><b>Select run to analyze:</b></h3>
	<select onchange="this.form.submit()" name="rundir" id="rundir" style="font-weight: bold; margin-left: 25px" >
	<?php
		echo '<option >-----SELECT RUN HERE-----</option>';
		$scan = scandir( $_POST['runrepo'] , $SCANDIR_SORT_DESCENDING = 1);
		foreach($scan as $dir)
		{
			if (isset($_POST['runrepo']) && isset($_POST['rundir']) && $_POST['rundir'] == $dir) {
				echo '<option selected="selected" value="'.$dir.'" >' . $dir . '</option>';
				//break;
			}
			else {
				if (is_dir($_POST['runrepo']."/".$dir) and $dir[0]!=='.' and $dir !== 'archive' and $dir !== 'Archive')
				{
					echo '<option value="'.$dir.'" >' . $dir . '</option>';
				}
			}
		}
	?>
    </select>
<!--
    <script type="text/javascript">
		document.getElementById('rundir').value = "<?php echo $_GET['rundir'];?>";
	</script>
-->
    </p>
    
    <p>
	<input style="margin-left: 25px" type="checkbox" name="forceCheckbox" value="Yes"
    <?php
		if (isset($_POST['forceCheckbox']) && $_POST['forceCheckbox'] == 'Yes' && isset($_POST['button'])){
			echo ' checked';
		}
	?>> Force overwrite of working directory (intermediate) files </input>
	<br>
	<input style="margin-left: 25px" type="checkbox" name="skipReadsProcessingCheckbox" value="Yes"
    <?php
		if (isset($_POST['skipReadsProcessingCheckbox']) && $_POST['skipReadsProcessingCheckbox'] == 'Yes' && isset($_POST['button'])){
			echo ' checked';
		}
	?>> Skip reads processing and try to use previous results? [Must check 'force' above] </input>
	</p>
    
    <p><b>Run analysis:</b></p>
	<button type="submit" name="button" style="margin-left: 25px;height: 50px;width: 120px"<?php 
		if (isset($_POST['rundir']) && isset($_POST['button'])) {
			echo ' disabled>IN PROGRESS SEE BELOW</button>';
		}
		elseif (isset($_POST['rundir']) && $_POST['rundir'] !== '-----SELECT RUN HERE-----' && isset($_POST['runrepo']) ) {
			echo ' ><b>ANALYZE</b></button>'; 
		}
		else {
			echo ' disabled>SELECT RUN</button>';
		}
		echo '<br>';
	?>
    </br>
    <?php if (isset($_POST['button'])) { 

        function run_in_background($Command, $Priority = 0) {
            if($Priority)
               $PID = shell_exec("nohup nice -n $Priority $Command 2> /dev/null & echo $!");
            else
               $PID = shell_exec("nohup $Command 2> /dev/null & echo $!");
            return($PID);
        }

        function is_process_running($PID) {
           //exec("ps $PID", $ProcessState);
           //$cnt = count($ProcessState);
           //exec("kill -0 $PID", $ProcessState2);
           //echo var_dump($ProcessState2);
           //echo("<p>$cnt </p>");
           //if (count($ProcessState) >= 2) return True;
           //else return False;
           
           #echo posix_getpgid($PID);
           ##return posix_getpgid($PID);
           
           if (file_exists( "/proc/$PID" )){
			   //echo("<p>RUNNING!</p>");
			   return True; 
			}
			else {
				//echo("<p>NOT RUNNING!</p>");
				return False;
			}
        }

        date_default_timezone_set('America/Los_Angeles');
	//$timestamp = date("ymd_Hi", time());
        //$analysis = str_replace('.R', '', $_POST['analysis']);

        if (isset($_POST['rundir']) && $_POST['rundir'] !== '-----SELECT RUN HERE-----' && isset($_POST['runrepo'])) {

		   //$cmd = 'nohup echo $USER & echo $!';
           //$cmd = "nohup " . $PYTHON_EXE . " " . $prod_location . '/' . $TP_Wrapper .
            //    " --pipeline_path " .  "$TP_DIR/{$_POST['analysis']}" .
             //     " --basecalls_dir $data_location/runs/{$_POST['rundir']}/Data/Intensities/BaseCalls/ --multicore " . $MAX_CORE . " & echo $!";

           $cmd = "nohup $PYTHON_EXE $TP_BASE/$TP_Wrapper -i {$_POST['runrepo']}/{$_POST['rundir']}/";
           //$cmd = "nohup " . $PYTHON_EXE . " /mnt/rnd/1604/" . $Run_type . '/' . $TP_Wrapper . 
                  
           if(isset($_POST['forceCheckbox']) && $_POST['forceCheckbox'] == 'Yes') {
			   $cmd = $cmd . " --force";
		   }
		   if(isset($_POST['skipReadsProcessingCheckbox']) && $_POST['skipReadsProcessingCheckbox'] == 'Yes') {
			   $cmd = $cmd . " --resume";
		   }
		   
		   $cmd = $cmd . " 2>&1 & echo PID: $!"; 

           $descriptorspec = array(
              0 => array("pipe", "r"),   // stdin is a pipe that the child will read from
              1 => array("pipe", "w"),   // stdout is a pipe that the child will write to
              2 => array("pipe", "w")    // stderr is a pipe that the child will write to
           );
           ob_implicit_flush(true);ob_end_flush();
           echo "<p>";
           #echo 'Current script owner: ' . get_current_user(); 
           echo "Command Line Program and Options: ";
           echo($cmd);
           echo "</p>";
           ?>
<!--
           <p>EGFR suite takes less time, BRAF and KRAS may take up to 30 min.</p>
-->
           <?php
           //flush();
           //$ps = run_in_background($cmd);
           $process = proc_open($cmd, $descriptorspec, $pipes, realpath('./'), NULL);
           if (is_resource($process)) {
             //echo("<p>In progress, please do not refresh your browser... Using " . $process . "</p>");
             echo("<p>In progress, please do not refresh or close your browser...</p>");
             $status = proc_get_status($process);
             $pid = $status['pid']; 
             //echo("<p>Server side process ID: " . $pid); 
             echo("<p style=\"margin-left: 40px\">"); 
             //while (is_process_running($pid) && ($s = stream_get_line($pipes[1], 10000, "\n"))) {
             while ($s = fgets($pipes[1])) {
             //while (file_exists( "/proc/$pid" )) {
             //while (is_process_running($pid)) {
			   #echo("<p>/proc/$pid RUNNING!</p>");
			   //$s = stream_get_line($pipes[1], 4096, "\n");
			   //if (strlen($s)>0) {
				//echo print_r($s);
				echo("<br>");
				//echo(str_pad($s, 10000));
				echo($s);
				flush();
				//sleep(10);
			   //}
			   //else sleep(20);
               //}
             }
             echo("<p>Job completed as noted above. Output files located as noted below. Refresh browser or select new run to start new analysis. </p>");
           }
           $exitcode = proc_close($process);
         }
         //echo "</pre>";
         

      }
    ?>
    </p>
        <?php include 'include/support.php'?>
        <?php include 'include/results.php'?>
	</body>
	<br>
	<br>
	<br>
        <?php include 'include/showConfigAsTable.php'?>

<!--
    
    <?php include 'include/contact.php'?>
    </p>
 <h3>DEV pipelines information:</h3>
	<?php include 'include/devInfo.php'?>
    <h3>Updates</h3>
    <?php include 'include/updates.php'?>
    <h3>Release Information: </h3>
    <?php include 'include/releases.php'?>
-->
 
</html>
