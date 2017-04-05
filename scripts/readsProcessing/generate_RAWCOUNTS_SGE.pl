#!/usr/bin/perl

## Usage: perl generate_RAWCOUNTS_SGE.pl --basecallsDir /path/to/run/Data/Intensities/BaseCalls --samplesheet /path/to/SampleSheet.csv --config /path/to/config.ini [--sge flag to use SGE scheduler] [--force force overwrite of output directory] [--help] [--tool] [--environment] [--mode]

use strict;
use warnings;
$|++;
use File::Basename;
use Cwd qw(abs_path);
my $scriptDir = "";
BEGIN {
	use File::Spec::Functions qw(rel2abs canonpath catdir catfile curdir updir splitpath splitdir catpath);
	sub cwd2 {
		my $cwd = dirname(rel2abs($0));
		my @s = split("/scripts/readsProcessing", $cwd);
		return $s[0];
	}
	#$scriptDir = rel2abs($0);
	#$scriptDir = dirname($0);
	$scriptDir = cwd2();
	#print "Using script dir: $scriptDir\n";
	unshift @INC, "$scriptDir";
	$scriptDir = dirname(rel2abs($0));
	unshift @INC, "$scriptDir";
}
$scriptDir = dirname($0);
use Schedule::SGELK;
use File::Tee qw(tee);
use File::Path 'make_path';
use Parallel::Loops;
use List::MoreUtils qw(uniq);
use String::Approx 'aindex';
use Getopt::Long; 
use DateTime;
use DateTime::Format::Human::Duration;
use File::Copy qw(copy);
use File::Find;
use Data::Dumper;
use List::MoreUtils qw(first_index);
use IPC::Run qw(run);
use XML::Simple;
use Config::IniFiles;
use Sys::Hostname;
use Array::Utils qw(:all);

print "\n";
print qx/ps -o args $$/;
print "\n\n";

my $hostname = hostname;
print "HOSTNAME: $hostname\n";
my $user = $ENV{LOGNAME} || $ENV{USERNAME} || $ENV{USER} || getpwuid( $< );
print "USERNAME: $user\n";

my $dtStart = DateTime->now;

## Usage: perl generate_RAWCOUNTS_SGE.pl --basecallsDir /path/to/run/Data/Intensities/BaseCalls --samplesheet /path/to/SampleSheet.csv --config /path/to/config.ini [--sge flag to use SGE scheduler] [--force force overwrite of output directory] [--help] [--environment] [--mode]
## load commandline input variables
my %inputs = (); 
GetOptions( \%inputs, 'help|h', 'basecallsDir:s', 'samplesheet:s', 'config:s','sge','force|f', 'tool:s', 'environment:s', 'mode:s'); 

# if help is requested
if ($inputs{help}) {
	Usage();
	exit 0;
}

# figure out base directory from current dir ../scripts/readsProcessing
my $baseDir = $scriptDir;
my @dirs = splitdir($baseDir);
#print "DIR: $scriptDir\n"; sleep 60;
# go one dir up to ../scripts
#$baseDir = updir($baseDir);
pop(@dirs);
# go one more dir up to ..
#$baseDir = updir($baseDir);
pop(@dirs);
# final base dir
#$baseDir = rel2abs($baseDir);
$baseDir = catdir(@dirs);
if (!-d $baseDir) {
	print "Base pipeline directory: $baseDir\n";
	die "ERROR: Base pipeline directory $baseDir not found! $!\n";
}
else {
	print "Base pipeline directory: $baseDir\n";
	print "Current working directory: ". cwd2(). "\n";
}

#my $toolVersion = qx(cd $baseDir; git rev-parse --short HEAD);
#$toolVersion = "6.0.0.".$toolVersion;
my $toolVersion = $inputs{tool};
chomp($toolVersion);
print "Tool version: $toolVersion\n";

### MAKE SURE BASIC SCRIPT INPUTS EXIST
# check and load config file
my $config;
if (defined $inputs{config} && -e $inputs{config}) {
	$inputs{config} = abs_path($inputs{config});
	$config = Config::IniFiles->new( -file => $inputs{config} ) or die "ERROR: unable to load config file : $inputs{config} : $!\n";
	print "Using config file: $inputs{config}\n";
}
else {
	Usage();
	die "ERROR: --config file must be defined and exist : $inputs{config} : $!\n";
}
# make sure basecalls dir exists
if (defined $inputs{basecallsDir} && -d $inputs{basecallsDir}) {
	$inputs{basecallsDir} = abs_path($inputs{basecallsDir});
	print "Using basecalls directory: $inputs{basecallsDir}\n";
}
else {
	Usage();
	die "ERROR: --basecallsDir directory must be defined and exist : $inputs{basecallsDir} : $!\n";
}
# make sure samplesheet csv exists
if (defined $inputs{samplesheet} && -e $inputs{samplesheet}) {
	$inputs{samplesheet} = abs_path($inputs{samplesheet});
	print "Using samplesheet: $inputs{samplesheet}\n";
}
else {
	Usage();
	die "ERROR: --samplesheet file must be defined and exist : $inputs{samplesheet} : $!\n";
}

### GET RUNID
my $runId = getRunId($inputs{basecallsDir});
print "Identified runId: $runId from folder name\n";

### MAKE WORKING AND OUTPUT FOLDERS
my $workingDir = $config->val('global','workingDir') or die "ERROR: workingDir must be defined in config file $inputs{config}\n";
if (!-d "$workingDir/$runId") {
	make_path("$workingDir/$runId") or die "ERROR: unable to create working directory : $workingDir/$runId : $!\n";
	make_path("$workingDir/$runId/temp") or die "ERROR: unable to create working temp directory : $workingDir/$runId/temp : $!\n";
	$inputs{tempDir} = "$workingDir/$runId/temp";
	print "Working directory: $workingDir/$runId\n";
}
elsif ($inputs{force}) {
	print "Working directory: $workingDir/$runId exists but will be overwritten due to --force\n";
	if (!-d "$workingDir/$runId/temp") {
		make_path("$workingDir/$runId/temp") or die "ERROR: unable to create working temp directory : $workingDir/$runId/temp : $!\n";
	}
	# delete all old files in directory
	find( { wanted => \&findDeleteFilesInDir, no_chdir => 1 }, "$workingDir/$runId");
	find( { wanted => \&findDeleteFilesInDir, no_chdir => 1 }, "$workingDir/$runId/temp");
	$inputs{tempDir} = "$workingDir/$runId/temp";
}
else {
	die "ERROR: workingDir $workingDir/$runId already exists! Use --force to override!\n";
}
my $outputDir = $config->val('global','outputDir') or die "ERROR: outputDir must be defined in config file $inputs{config}\n";
if (!-d "$outputDir/$runId") {
	make_path("$outputDir/$runId") or die "ERROR: unable to create output directory : $outputDir/$runId : $!\n";
	print "Output directory: $outputDir/$runId\n";
}
elsif ($inputs{force}) {
	print "Output directory: $outputDir/$runId exists but will be overwritten due to --force\n";
	# delete all old files in directory
	#find( { wanted => \&findDeleteFilesInDir, no_chdir => 1 }, "$outputDir/$runId");
}
else {
	die "ERROR: outputDir $outputDir/$runId already exists! Use --force to override!\n";
}

### COPY AND LOAD SAMPLESHEET
#copy ($inputs{samplesheet}, "$workingDir/$runId") or die "ERROR: Unable to copy samplesheet $inputs{samplesheet} to workingDir $workingDir/$runId: $!\n";
# get assay and other info from sampleSheet
my $sampleAssayHashRef = getAssayFromSampleSheetFile($inputs{samplesheet});
my %sampleAssayHash = %$sampleAssayHashRef;
print "SampleSheet loaded okay!\n";

### PARSE BASECALLS FOLDER FOR FASTQ FILES
my @fastqFilePaths;
# find and load fastq files # find fastq.gz files in BaseCalls dir
opendir(DIR, $inputs{basecallsDir}) or die "ERROR: could not open $inputs{basecallsDir} $!\n";
my @files = sort {(stat "$inputs{basecallsDir}/$b")[7] <=> (stat "$inputs{basecallsDir}/$a")[7]} readdir(DIR); # try to process large files first
foreach my $file (@files) {
	# We only want files
	next unless (-f catfile($inputs{basecallsDir},$file));
	# Use a regular expression to find files ending in .fastq.gz
	next unless ($file =~ m/\.fastq.gz$/);
	# Use a regex to find files that do not have index read or undetermined or previously processed
	next if ($file =~ m/(I1|Undetermined|_trimmed)/ig);
	next if ($file =~ m/(_I1_|_i1_)/ig);
	# push filenames and paths
	$file = rel2abs(catfile($inputs{basecallsDir},$file));
	push (@fastqFilePaths, $file);	
}
closedir(DIR);

# sort list by file size to process larger files first
my $fqRef = sortFastqsBySize(\@fastqFilePaths);
@fastqFilePaths = @$fqRef;

### MAKE SURE THAT EQUAL NUMBER OF FASTQS and SAMPLES FROM SAMPLESHEET
if (scalar(@fastqFilePaths) != (scalar keys %sampleAssayHash)) {
	print "FASTQ Files found in $inputs{basecallsDir}: ".scalar(@fastqFilePaths)."\n";
	print "Samples found on sampleSheet: ".(scalar keys %sampleAssayHash)."\n";
	die "ERROR: Unequal number of fastq files and samples found!\n\n";
}

### SET EVIRONMENT VARIABLES
$ENV{SGE_ROOT} = $config->val('global','SGE_ROOT');
$ENV{PWD} = "$workingDir/$runId/temp/";

##### DEBUG #####
# print global options
print "\n";
print "Using [global] options: \n";
my @globalParams = $config->Parameters('global');
foreach my $param (@globalParams) {
	print "\t$param = ".$config->val('global',$param)."\n";
}
print "\n";
print "Using [readsProcessing] options: \n";
my @readsParams = $config->Parameters('readsProcessing');
foreach my $param (@readsParams) {
	if ( $param !~ /server|sleep/i ) {
		my $relPath = $config->val('readsProcessing',$param);
		#my $fullPath = catfile( cwd(), $inputs{'mode'}, $relPath );
		my $fullPath = catfile( cwd2(), $relPath );
		# set config file info to full path
		$config->setval('readsProcessing',$param,$fullPath);
	}
	print "\t$param = ".$config->val('readsProcessing',$param)."\n";
	#print "\t\tfullPath = $fullPath\n";
}

####################
##### DO STUFF #####
####################

# extract cluster info
print "\n";
print "Extracting cluster info from";
my @xmlFiles;
my $clusterInfoRef = getClusterInfo(\@fastqFilePaths, $inputs{basecallsDir});
my %clusterInfo = %$clusterInfoRef;
print "...done\n";

# set up variables for parallel processing
my $pl = Parallel::Loops->new($config->val('global','jobs'));
$pl->share(\@fastqFilePaths);
$pl->share(\%sampleAssayHash);
$pl->share(\%inputs);

# set up SGE stuff
my $sge;
if ($inputs{sge}) {
	print "\n";
	print "Using SGE wrapper queue: ".$config->val('global','wrapperQueue')."\n";
	print "Using SGE process queue: ".$config->val('global','processQueue')."\n";
	print "Using parallel environment: ".$config->val('global','pe')."\n";
	$sge=Schedule::SGELK->new(verbose=>1,queue=>($config->val('global','wrapperQueue')),pe=>($config->val('global','pe')),numcpus=>1,workingdir=>"$inputs{tempDir}",waitForEachJobToStart=>0,qsubxopts=>'-l mem_free=2G');
	print "\n";
}

# process fastq files in parallel fashion
print "\n";
print "Processing fastq files in parallel fashion...\n";
#for (my $i=0; $i<scalar(@fastqFilePaths); $i++) {
#print "\@INC PATHS:\n"; print join("\n",@INC); print "\n"; sleep 600;
$pl->foreach (\@fastqFilePaths, sub {
	
	# from fastq filename, parse out sample number to associate with sampleAssayHash info
	my $fastqOrig = $_;
	my $index = first_index { $_ =~ /$fastqOrig/i } @fastqFilePaths;
	#my $fastqOrig = $fastqFilePaths[$i];
	my $name = basename($fastqOrig,".fastq.gz");
	
	# set up sample-specific log file
	open (LOG,'>',"$workingDir/$runId/$name"."_log.txt");
	
	print LOG "Processing sample : $name\n";
	my ($sampleName, $sampleNumber) = getFastqInfo($name);
	
	# get assay and source combo and check to make sure it is defined in config file
	my $ref = $sampleAssayHash{$sampleNumber};
	my %sampleHash = %$ref;
	
	#print Dumper(\%sampleHash); print "\n";
	
	my $assaySource = $sampleHash{'Sample_Project'} ."_". $sampleHash{'Source'};
	#print "assaySource: $assaySource\n";
	if (!$config->SectionExists($assaySource)) {
		die "ERROR: assay_source combo parameters must be defined in config file!\n\tFound Assay: ".$sampleHash{'Sample_Project'}." Source: ".$sampleHash{'Source'}."\n";
	}
	##### DEBUG #####
	else {
		print LOG "Using [$assaySource] options: \n";
		my @assayParams = $config->Parameters($assaySource);
		foreach my $param (@assayParams) {
			print LOG "\t$param = ".$config->val($assaySource,$param)."\n";
		}
	}
	
	### LAUNCH SUBSCRIPT FOR INDIVIDUAL FASTQ FILE
	## Usage: perl generate_RAWCOUNTS_singleFastq.pl --fastq /Data/Intensities/BaseCalls/input.fastq --outdir /path/to/outfolder --tempdir /path/to/outfolder/temp --cpus cpus/jobs --Qmin minQscore N --MAPQmin N --mismatch 0.N --percentBases N --bwaMaxGaps N --bwaMaxGapExts N --bwaGapOpenPen N --bwaGapExtPen N --bwaMismatchPen N --ref reference fasta --assay sample assay --input input volume 10/60 --source sample source P/U --mtCoordsFile mutant coordinates file --adaptersFile adapter seqs to trim --primersFile seqs to flag primer-dimers --targetsFile assay targets file [--sge flag to use SGE scheduler] [--sgeQ SGE queue to submit to] [--sgePE SGE parallel environment name] --runId runId of run [[--mode 1/2]]  [--keepTemp] [--noTrimming] [--Nmask] [--minlen minimum read length after trimming] [--overlap minimum number of bases to trim] [--clustersRaw] [--clustersPF] [--type] [--tool] [--samplePlate] [--sampleWell] [--i7IndexID] [--index] [--standardGroup] [--batch] [--checkoutNumber] [--ngPerRxn] [--phixFraction] [--projectVersion] --CUTADAPT --FASTQ_QUAL_FILTER --BWA --SAMTOOLS --BAMREADCOUNT --FASTQC --IGVLIB --IGV --BAMSTATS [--environment]
	
	## try to dyanamically allocate correct number cpu cores
	# give top third fastqs by size full cores, next third half cores, last third quarter cores
	my $cores = $config->val('global','cores');
	my $total = scalar(@fastqFilePaths);
	if (($index/$total) <= 0.3333) {
		$cores = $cores;
	}
	elsif (($index/$total) <= 0.6666) {
		$cores = int($cores/2);
	}
	else {
		$cores = int($cores/4);
	}
	
	### set up intial command line
	
	# basic run and global info
	my $CMD = "perl ".$config->val('readsProcessing','COUNT')." --fastq $fastqOrig --outdir $workingDir/$runId --tempdir $workingDir/$runId/temp --cpus $cores --tool $toolVersion --runId $runId --environment $inputs{'environment'}";
	if ($config->val('global','outputBAMSTATS') =~ /true/i ) {
		$CMD = $CMD . " --outputBAMSTATS";
	}	
	
	# add info from [readsProcessing] section
	$CMD = $CMD . " --adaptersFile ".$config->val('readsProcessing','adaptersFile')." --primersFile ".$config->val('readsProcessing','primersFile')." --targetsFile ".$config->val('readsProcessing','targetsFile')." --CUTADAPT ".$config->val('readsProcessing','CUTADAPT')." --FASTQ_QUAL_FILTER ".$config->val('readsProcessing','FASTQ_QUAL_FILTER')." --BWA ".$config->val('readsProcessing','BWA')." --SAMTOOLS ".$config->val('readsProcessing','SAMTOOLS')." --BAMREADCOUNT ".$config->val('readsProcessing','BAMREADCOUNT')." --FASTQC ".$config->val('readsProcessing','FASTQC')." --IGVLIB ".$config->val('readsProcessing','IGVLIB')." --IGV ".$config->val('readsProcessing','IGV')." --BAMSTATS ".$config->val('readsProcessing','BAMSTATS')." --IGVSERVER ".$config->val('readsProcessing','IGVSERVER')." --MAXSLEEPDELAY ".$config->val('readsProcessing','MAXSLEEPDELAY');
	
	# add info from [assaySource] section
	my $relPath = $config->val($assaySource,'mtCoordsFile');
	my $relPath2 = $config->val($assaySource,'referenceFile');
	#my $fullPath = catfile( cwd(), $inputs{'mode'}, $relPath );
	my $fullPath = catfile( cwd2(), $relPath );
	my $fullPath2 = catfile( cwd2(), $relPath2 );
	# set config file info to full path
	$config->setval($assaySource,'mtCoordsFile',$fullPath);
	$config->setval($assaySource,'referenceFile',$fullPath2);

	
	$CMD = $CMD . " --mtCoordsFile ".$config->val($assaySource,'mtCoordsFile')." --Qmin ".$config->val($assaySource,'Qmin')." --MAPQmin ".$config->val($assaySource,'MAPQmin')." --mismatch ".$config->val($assaySource,'mismatch')." --percentBases ".$config->val($assaySource,'percentBases')." --bwaMaxGaps ".$config->val($assaySource,'bwaMaxGaps')." --bwaMaxGapExts ".$config->val($assaySource,'bwaMaxGapExts')." --bwaGapOpenPen ".$config->val($assaySource,'bwaGapOpenPen')." --bwaGapExtPen ".$config->val($assaySource,'bwaGapExtPen')." --bwaMismatchPen ".$config->val($assaySource,'bwaMismatchPen')." --minlen ".$config->val($assaySource,'minlen')." --overlap ".$config->val($assaySource,'overlap')." --ref ".$config->val($assaySource,'referenceFile');
	
	# add assay-specific countMode
	$CMD = $CMD . " --mode ".$config->val($assaySource,'countMode');
	
	# add sample-specific info
	# load cluster info
	my $clustersRaw = $clusterInfo{$sampleNumber}{clustersRaw};
	my $clustersPF = $clusterInfo{$sampleNumber}{clustersPF};
	#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Standard_Group,Description,Input,Source,Batch,Checkout_Number,NG_per_RXN,PhiX_Fraction,Project_Version
	$CMD = $CMD . " --clustersRaw $clustersRaw --clustersPF $clustersPF --assay $sampleHash{Sample_Project} --input $sampleHash{Input} --source $sampleHash{Source} --type $sampleHash{Description} --samplePlate $sampleHash{Sample_Plate} --sampleWell $sampleHash{Sample_Well} --i7IndexID $sampleHash{I7_Index_ID} --index $sampleHash{index} --standardGroup $sampleHash{Standard_Group} --batch $sampleHash{Batch} --checkoutNumber $sampleHash{Checkout_Number} --ngPerRxn $sampleHash{NG_per_RXN} --phixFraction $sampleHash{PhiX_Fraction} --projectVersion $sampleHash{Project_Version}";
	
	#foreach (@INC) {
		#my $path = $_;
		#if (-e "$path/Schedule/SGELK.pm") {
			#print "FOUND: $path/Schedule/SGELK.pm\n\n";
		#}
	#}
	#sleep 120;
	
	#IF SGE
	if ($inputs{sge}) {
		# clean up name
		my $jname = $name;
		#$jname =~ s/^[0-9]+_//ig;
		#$jname =~ s/^-+//ig;
		#$jname =~ s/^_+//ig;
		$sge->set("jobname",$jname);
		$sge->set("seed",$sampleNumber);
		$CMD = "/usr/bin/time -v " . $CMD;
		$CMD = $CMD . " --sge --sgeQ ".$config->val('global','processQueue')." --sgePE ".$config->val('global','pe');
		print LOG "\nRunning command: $CMD\n\n";
		close LOG;
		$sge->pleaseExecute_andWait("$CMD");
	}
	else {
		$CMD = "/usr/bin/time -v " . $CMD;
		$CMD = $CMD . " >> $workingDir/$runId/$name"."_log.txt 2>&1";
		print LOG "\nRunning command: $CMD\n\n";
		close LOG;
		run($CMD) or die "ERROR: Failed to run $CMD: $!\n\n";
	}
	
	# clean up intermediate files
	my @exts = (".fastq.gz\$",".sam\$",".sai\$",".submitted\$",".running\$",".finished\$",".zip\$");
	#print "\n";
	#print "Cleaning up intermediate files...\n";
	my $search = "(" . join("|",@exts) . ")";
	#print "SEARCH STRING: $search\n"; sleep (120);
	opendir( DIR, "$workingDir/$runId/temp" ) or die "Can't read $workingDir/$runId/temp : $!\n";
	while (my $file = readdir(DIR)) {
		if ($file =~ /$search/i && $file =~ /$name/i) {
			#print "REMOVING FILE: $file\n"; sleep 120;
			unlink catfile("$workingDir/$runId/temp",$file);
			#unlink glob($file);
		}
	}
	opendir( DIR, "$workingDir/$runId" ) or die "Can't read $workingDir/$runId : $!\n";
	while (my $file = readdir(DIR)) {
		if ($file =~ /$search/i && $file =~ /$name/i) {
			unlink catfile("$workingDir/$runId",$file);
			#unlink glob($file);
		}
	}
	
	print "\n";
	print "\t===PROCESSING $name COMPLETE===\n";
	print "\n";
	#sleep 120;

});
# wait for all SGE jobs to finish
if ($inputs{sge}) {
	$sge->wrapItUp();
}
print "\n\n";

### FIND AND MERGE ALL sample specific rawCounts.csv
my @csvFiles;
find( { wanted => \&findRawCountsCSV, no_chdir => 1 }, "$workingDir/$runId");
if (scalar(@csvFiles) < 1) {
	die "ERROR: No sample-specific csv files found!\n";
}
if (scalar(@csvFiles) != scalar(@fastqFilePaths)) {
	# get only sample basenames
	my @csvBase = @csvFiles;
	foreach my $file (@csvFiles) {
		$file = basename($file, qr/\Q_*_*_*_*_*_rawCounts.csv\E/);
		push @csvBase, $file;
	}
	my @fastqBase = @fastqFilePaths;
	foreach my $file (@fastqFilePaths) {
		$file = basename($file, ".fastq.gz");
		push @fastqBase, $file;
	}
	my @minus;
	# usually less csvFiles vs fastqFiles
	if (scalar(@csvFiles) < scalar(@fastqFilePaths)) {
		# get items from array @fastqBase that are not in array @csvBase
		@minus = array_minus( @fastqBase, @csvBase );
	}
	elsif (scalar(@csvFiles) > scalar(@fastqFilePaths)) {
		# get items from array @csvBase that are not in array @fastqBase
		@minus = array_minus( @csvBase, @fastqBase );
	}
	
	#die "ERROR: One or more sample-specific csv files not found!\n\tFound ".scalar(@csvFiles)." files\n\tExpected ".scalar(@fastqFilePaths)." files\n\t Missing samples:\n\t\t".join("\n\t\t",@minus)."\n";
	die "ERROR: One or more sample-specific csv files not found!\n\tFound ".scalar(@csvFiles)." files\n\tExpected ".scalar(@fastqFilePaths)." files\n\n";
}

# merge sample-specific files into one big file
my $timestamp = getDateTimeStamp();
#my $outFile = catfile("$workingDir/$runId",($runId."_".$timestamp."_RAWCOUNTS.csv"));
my $outFile = catfile("$workingDir/$runId",($runId."_RAWCOUNTS.csv"));
print "\n";
print "Generating merged RAWCOUNTS file : $outFile\n\n";
my $header="";
my %bodyHash;
foreach my $csv (@csvFiles) {
	open (FILE, '<', $csv);
	chomp( my @lines = <FILE> );
	close FILE;
	
	$header = $lines[0];
	for (my $i=1; $i<scalar(@lines); $i++) {
		my @s = split(",",$lines[$i]);
		chomp($lines[$i]);
		chomp(@s);
		#RunId,RunFolder,SampleNumber,Name,Assay,Input,Source,ExpectedCN,Type,Tool,SamplePlate,SampleWell,I7IndexID,Index,StandardGroup,Batch,CheckoutNumber,ngPerRxn,PhixFraction,ProjectVersion,ClustersRaw,ClustersPF,RawReads,TrimmedReads,TrimmedFilteredReads,TotalMappedReads,TotalTargetReads,PhiXReads,PrimerArtifacts,Other,OTA,TargetWTReads,Chr,Start,Sequence,Count
		my $key = $s[2]."_".$s[-3]."_".$s[-2];
		$bodyHash{$key} = $lines[$i];
	}
}
# print out merged file
open(OUT, '>', $outFile) or die "ERROR: Could not open file $outFile for printing $!\n";
print OUT "$header\n";
foreach my $key (sort my_complex_sort keys %bodyHash) {
	print OUT "$bodyHash{$key}\n";
}
close OUT;
# copy merged file to output dir
#copy($outFile,"$outputDir/$runId");

### FINISH UP STUFF

# exit IGV if running here
if (!$inputs{sge}) {
	exitIGV();
}
#sleep(30);

# final info
print "\n\n";
print "Start time: "; print join ' ', $dtStart->ymd, $dtStart->hms; print "\n";
my $dtEnd = DateTime->now;
print "End time: "; print join ' ', $dtEnd->ymd, $dtEnd->hms; print "\n";
my $span = DateTime::Format::Human::Duration->new();
print 'Total elapsed time: ', $span->format_duration_between($dtEnd, $dtStart); print "\n\n";
print "=====PROCESSING $runId COMPLETE=====\n";
print "\n";










sub loadTargetsFile {
	my $file = shift;
	# load assay targets file
	open (TARGETS, '<', $file);
	chomp( my @targets = <TARGETS> );
	close TARGETS;
	return \@targets;
}

sub loadFastqListFile {
	my $file = shift;
	# load assay targets file
	open (FILE, '<', $file);
	chomp( my @list = <FILE> );
	close FILE;
	# loop thru list and make sure each file exists
	for (my $i=0; $i<scalar(@list); $i++) {
		$list[$i] = rel2abs($list[$i]);
		if (!-e $list[$i]) {
			die "ERROR: Fastq file at line $i in $file not found! $!\n";
		}
	}
	@list = sort {(stat "$b")[7] <=> (stat "$a")[7]} @list; # try to process large files first
	return \@list;
} 


sub sortFastqsBySize {
	my $fastqRef = shift;
	my @fastqs = @$fastqRef;
	#print "\tFASTQS in: " . scalar(@fastqs) . "\n";
	@fastqs = sort {(stat "$b")[7] <=> (stat "$a")[7]} @fastqs; # try to process large files first
	#print "\tFASTQS out: " . scalar(@fastqs) . "\n";
	return \@fastqs;
}


sub getFastqInfo {
	my $fastqName = shift;
	my @s = split("_",$fastqName);
	#MDJ88-U-R1-C1_S35_L001_R1_001_trimmed.fastq.gz
	my $sampleName = $s[0];
	my $sampleNumber = $s[1];
	$sampleNumber =~ s/S//i;
	
	return ($sampleName, $sampleNumber);
}

sub getAssayFromSampleSheetFile {
	my $sampleSheetFile = shift;
	my @sampleSheet;
	#my $assay = "NA";
	my %sampleAssayHash;
	open SS, '<', $sampleSheetFile;
	while (<SS>) {
		#my $doOut = 0;
		my $line = $_;
		chomp($line);
		next if ($line =~ m/^#/i);
		next if ($line eq "\r");
		push @sampleSheet, $line;
		
	}
	close SS;
	#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Standard_Group,Description,Input,Source,Batch,Checkout_Number,NG_per_RXN,PhiX_Fraction,Project_Version
	my @headerNames;
	# figure out what line the [Data] header is on
	my $headerIdx = 0;
	for (my $i=0; $i<scalar(@sampleSheet); $i++) {
		my $line = $sampleSheet[$i];
		chomp($line);
		if ($line =~ m/^Sample_ID/) {
			$headerIdx = $i;
			@headerNames = split(",",$line);
			chomp(@headerNames);
			for (my $i=0; $i<scalar(@headerNames); $i++) {
				$headerNames[$i] =~ s/^\s+|\s+$//g;
				$headerNames[$i] =~ s/\R//g;
			}
		}
	}
	#$headerIdx = $headerIdx + 1;
	#print "HEADER LINE IDX: $headerIdx\n"; sleep(120);
	
	# figure out what index the Sample_project field is
	my $idx = -1;
	my $inputIdx = -1;
	my $sourceIdx = -1;
	my @s = split(",",$sampleSheet[$headerIdx]);
	if ($sampleSheet[$headerIdx] !~ m/^sample_id/i) {
		$headerIdx++;
		@s = split(",",$sampleSheet[$headerIdx]);
	}
	for (my $i=0; $i<scalar(@s); $i++) {
		if ($s[$i] =~ m/sample_project/i) {
			# figure out what index the Sample_project field is
			$idx = $i;
			#print "\n\tSample_Project found at $idx\n\n";
			#last;
		}		
		elsif ($s[$i] =~ m/^input/i) {
			$inputIdx = $i;
		}
		elsif ($s[$i] =~ m/^source/i) {
			$sourceIdx = $i;
		}
	}
	
	my @sampleNumber;
	my $num = 1; # automatically renumber sampleNumber starting with 1
	for (my $i = ($headerIdx+1); $i<scalar(@sampleSheet); $i++) {
		next if ($sampleSheet[$i] =~ m/^#/i);
		my @s = split(",",$sampleSheet[$i]);
		
		push @sampleNumber, $s[0];
		#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Standard_Group,Description,Input,Source,Batch,Checkout_Number,NG_per_RXN,PhiX_Fraction,Project_Version
		
		# build a hash to save all the column values
		my %hash;
		for (my $i=0; $i<scalar(@headerNames); $i++) {
			$s[$i] =~ s/^\s+|\s+$//g;
			$s[$i] =~ s/\R//g;
			
			# first unify assay names
			if ($headerNames[$i] =~ m/sample_project/i) {
				if ($s[$i] =~ /(kras|G12)/i && $s[$i] !~ /(q61|rh|_2)/i) {
					$s[$i] = "KRAS_G12X"; }
				elsif ($s[$i] =~ /ex19|exon19|del/i && $s[$i] !~ /2/i) {
					$s[$i] = "EGFR_EX19DEL"; }
				elsif ($s[$i] =~ /l858/i && $s[$i] !~ /2/i) {
					$s[$i] = "EGFR_L858R"; }
				elsif ($s[$i] =~ /t790/i) {
					$s[$i] = "EGFR_T790M"; }
				elsif ($s[$i] =~ /braf/i && $s[$i] !~ /2/i) {
					$s[$i] = "BRAF_V600X"; }
				elsif (defined $s[$i] && exists $s[$i]) {
					$s[$i] = $inputs{assay}; }
			}
			
			# second unify source names
			if ($headerNames[$i] =~ m/source/i) {
				$s[$i] = uc($s[$i]);
				if ($s[$i] =~ /(P|W|B)/i) {
					$s[$i] = "P"; }
			}
			
			# third fill in plate name
			if ($headerNames[$i] =~ m/plate/i) {
				if ($s[$i] eq "") {
					$s[$i] = "NA"; }
			}
			
			# fourth normalize/fix column names
			if ($headerNames[$i] =~ m/^index$/i) {
				$headerNames[$i] = 'index';
			}
			elsif ($headerNames[$i] =~ m/NG_per_RXN/i) {
				$headerNames[$i] = 'NG_per_RXN';
			}
			elsif ($headerNames[$i] =~ m/PhiX_Fraction/i) {
				$headerNames[$i] = 'PhiX_Fraction';
			}
			
			$hash{$headerNames[$i]} = $s[$i];
		}
		# push to sampleAssayHash keyed from sampleNumber from re-numbering
		$sampleAssayHash{$num} = \%hash;
		$num++; #increment sampleNumber
	}
	return \%sampleAssayHash;
}


#sub getTargetFromAssay {
	#my $assay = shift;
	#my $target = "NA";
	#my $wtSeq = "NA";
	#foreach my $line (@targets) {
		#next if ($line =~ /^#/);
		##chr	start	stop	name	wtSeq
		#my @s = split("\t",$line);
		#if ($s[3] =~ m/$assay/i) {
			#$target = "$s[0]:$s[1]-$s[2]";
			#chomp($s[4]);
			#$wtSeq = $s[4];
			#last;
		#}
	#}
	#return ($target, $wtSeq);
#}

sub getMutantsCoordsFile {
	my $assay = shift;
	my $file = "NA";
	my $base = catfile($baseDir,"data");
	if ($assay =~ /kras_g/i) {
		#$file = "/home/palak/isilon/KRAS_G12X_mutants_coords.bed"; 
		$file = catfile($base,"KRAS_G12X_mutants_coords.bed"); }
	elsif ($assay =~ /ex19|exon19|del/i) {
		#$file = "/home/palak/isilon/EGFR_EX19DEL_mutants_coords.bed"; }
		$file = catfile($base,"EGFR_EX19DEL_mutants_coords.bed"); }
	elsif ($assay =~ /l858/i) {
		#$file = "/home/palak/isilon/EGFR_L858R_mutants_coords.bed"; }
		$file = catfile($base,"EGFR_L858R_mutants_coords.bed"); }
	elsif ($assay =~ /t790/i) {
		#$file = "/home/palak/isilon/EGFR_T790M_mutants_coords.bed"; }
		$file = catfile($base,"EGFR_T790M_mutants_coords.bed"); }
	elsif ($assay =~ /braf/i) {
		#$file = "/home/palak/isilon/BRAF_V600X_mutants_coords.bed"; 
		$file = catfile($base,"BRAF_V600X_mutants_coords.bed"); }
	if (-e $file) {
		return $file;
	}
	else {
		die "ERROR: Mutant coordinates file $file not found! $!\n";
	}
}

sub loadMutantsCoordsFile {
	my $file = shift;
	my @mutantsCoords;
	if ($file ne "NA") {
		$file = abs_path(glob($file));
		open MT, '<', $file;
		while (<MT>) {
			next if ($_ =~ m/^#/);
			chomp($_);
			push @mutantsCoords, $_;
		}
		close MT;
	}
	return \@mutantsCoords;
}

sub getMutantsHeader {
	my $file = shift;
	my @mtLines;
	open MT, '<', $file;
	while (<MT>) {
		next if ($_ =~ m/^#/);
		chomp($_);
		push @mtLines, $_;
	}
	close MT;
	
	my @mtNames;
	foreach my $line (@mtLines) {
		my @s = split("\t",$line);
		#chr	start	end	name	mutant
		chomp($s[3]);
		push @mtNames, $s[3];
	}
	
	@mtNames = sort @mtNames;
	my $mtHeader = join(",",@mtNames);
	
	return $mtHeader;
}

sub getMutantsCoords {
	my $assay = shift;
	my $file = "NA";
	my @mutantsCoords;
	if ($assay =~ /kras_g/i) {
		$file = "/home/palak/isilon/KRAS_G12X_mutants_coords.bed"; }
	elsif ($assay =~ /ex19|exon19|del/i) {
		$file = "/home/palak/isilon/EGFR_EX19DEL_mutants_coords.bed"; }
	elsif ($assay =~ /l858/i) {
		$file = "/home/palak/isilon/EGFR_L858R_mutants_coords.bed"; }
	elsif ($assay =~ /t790/i) {
		$file = "/home/palak/isilon/EGFR_T790M_mutants_coords.bed"; }
	elsif ($assay =~ /braf/i) {
		$file = "/home/palak/isilon/BRAF_V600X_mutants_coords.bed"; 
		}
	
	if ($file ne "NA") {
		$file = abs_path(glob($file));
		open MT, '<', $file;
		while (<MT>) {
			next if ($_ =~ m/^#/);
			push @mutantsCoords, $_;
		}
		close MT;
	}
	return (\@mutantsCoords, $file);
}


sub countPrimerDimers {
	my ($samRef, $primerFile, $assay) = @_;
	my @sam = @$samRef;
	$primerFile = abs_path(glob($primerFile));
	my $forwardPrimer = "";
	my $reversePrimer = "";
	
	my $primerDimerCount = 0;
	
	# open primer file and find forward/reverse primers based on assay
	open PRIMER, '<', $primerFile;
	chomp(my @primerLines = <PRIMER>);
	close PRIMER;
	
	for (my $i=0; $i<scalar(@primerLines); $i+=2) {
		my $header = $primerLines[$i];
		if ($header =~ m/$assay/i && $header =~ m/forward/i) {
			$forwardPrimer = $primerLines[$i+1];
		}
		elsif ($header =~ m/$assay/i && $header =~ m/reverse/i) {
			$reversePrimer = $primerLines[$i+1];
		}
	}
	
	# loop through unmapped reads SAM file to find primer-dimers
	foreach my $samLine (@sam) {
		#M03685:22:000000000-AEN0T:1:2113:5528:8081      0       chr7    55242447        37      57M     *       0       0       AATTCCCGTCGCTATCAAGGAATTAAGAGAAGCAACATCTCCGAAAGCCAACAAGGA       CCCCCGGGGGGGGGGGGGGG?FGEFFCCFGGGGGGGCEFGFGGGEGCFEGFFCDC<<        XT:A:U  NM:i:0  X0:i:1  X1:i:0  XM:i:0  XO:i:0  XG:i:0  MD:Z:57
		my @s = split("\t",$samLine);
		my $read = $s[9];
				
		# get index of where the forward primer matches
		my $forwardIndex = aindex("$forwardPrimer", ["i 20%"], $read);
		# get index of where the reverse primer matches
		my $reverseIndex = aindex("$reversePrimer", ["i 20%"], $read);
		
		# if both primers are found....
		#if ($forwardIndex != -1 && $reverseIndex != -1) {
		#	my $forwardEnd = $forwardIndex + length($forwardPrimer);
		#	if (abs($reverseIndex - $forwardEnd) <= 3) {
		#		$primerDimerCount++;
		#	}
		#}
		# if any one of the primers are found...
		if ($forwardIndex != -1 || $reverseIndex != -1) {
			#my $forwardEnd = $forwardIndex + length($forwardPrimer);
			#if (abs($reverseIndex - $forwardEnd) <= 3) {
				$primerDimerCount++;
			#}
		}
	}
	
	return $primerDimerCount;
}

sub findDeleteFilesInDir {
	if (-f $_) {
		my $name = $File::Find::name;
		if ($name =~ m/.csv$/ && $name =~ m/samplesheet/i) {
			
		}
		elsif ($name !~ m/stats/i && $name !~ m/_log.txt$/i) {
			unlink $name or warn "WARNING: Unable to delete file $name\n";
		}
		elsif ($name =~ m/stats/i && $name !~ m/.csv$/i) {
			unlink $name or warn "WARNING: Unable to delete file $name\n";
		}
		elsif ($name !~ m/_log.txt$/i && $name !~ m/$runId/i) {
			unlink $name or warn "WARNING: Unable to delete file $name\n";
		}
	}
}

sub findRawCountsCSV {
	if (-f $_) {
		my $name = $File::Find::name;
		if ($name =~ m/.csv/i && $name =~ m/_rawCounts/ && $name !~ m/binned/i) {
			push @csvFiles, $name;
		}
	}
}

sub findRunStatisticsXML {
	if (-f $_) {
		my $name = $File::Find::name;
		if ($name =~ m/.xml/i && $name =~ m/RunStatistics/i) {
			push @xmlFiles, $name;
		}
	}
}

sub isSimplyIncreasingSequence {
    my ($seq) = @_;

    unless (defined($seq)
            and ('ARRAY' eq ref $seq)) {
        die 'Expecting a reference to an array as first argument';
    }

    return 1 if @$seq < 2;

    my $first = $seq->[0];

    for my $n (1 .. $#$seq) {
        return unless $seq->[$n] == $first + $n;
    }

    return 1;
}

sub exitIGV {
	my $CMD = "ps -eo args | grep [i]gv.jar | wc -l";
	print "Checking if IGV is running...\n";
	my $return = qx($CMD);
	print "\tRESPONSE: $return\n";
	chomp($return);
	if (int($return) > 0) {
		print "IGV is running. Exiting IGV...\n";
		require($config->val('readsProcessing','IGVLIB'));
		my $socket = igv_connect();
		igv_exit($socket);
		sleep(60);
	}
}

sub getClusterInfo {
	my $ref = shift;
	my @fastqFilePaths = @$ref;
	my $runDir = shift;
	
	# first find all Alignment dirs
	my @dirs = glob("$runDir/Alignment*");
	if (scalar(@dirs) < 1) { die "\nERROR: Alignment directory not found in $runDir! Check demultiplexing output... \n\n"; }
	
	# sort the Alignment dirs to get newest dir first
	@dirs = sort {(stat $b)[10] <=> (stat $a)[10]} @dirs;
	my $alignmentDir = $dirs[0];
	
	# find RunStatistics.xml file
	find( { wanted => \&findRunStatisticsXML }, $alignmentDir);
	
	# load RunStatistics.xml file
	if (scalar(@xmlFiles) < 1) { die "\nERROR: RunStatistics.xml file not found in $alignmentDir! \n\n"; }
	print " from " . $xmlFiles[0] . " ...";
	my $xml = new XML::Simple;
	my $data = $xml->XMLin($xmlFiles[0]);
	my $ref2 = $data->{OverallSamples}{SummarizedSampleStatistics};
	my @array = @$ref2;
	
	# process samples in parallel fashion
	my %hashOut;
	my $pl = Parallel::Loops->new(qx(nproc));
	$pl->share(\@fastqFilePaths);
	$pl->share(\%hashOut);
	$pl->share(\@array);
	$pl->foreach (\@fastqFilePaths, sub {
	#for (my $i=0; $i<scalar(@fastqFilePaths); $i++) {
		#my $fastqOrig = $fastqFilePaths[$i];
		my $fastqOrig = $_;
		my $name = basename($fastqOrig,".fastq.gz");
		my ($sampleName, $sampleNumber) = getFastqInfo($name);
		## determine runPath from fastq file path
		#my $runPath = $fastqOrig;
		#$runPath =~ s/Data.*//;
		## find RunStatistics.xml file
		#find( { wanted => \&findRunStatisticsXML }, $runPath);
		## process RunStatistics.xml file
		#if (scalar(@xmlFiles) < 1) { die "ERROR: RunStatistics.xml file not found in $runPath! \n\n"; }
		#my $xml = new XML::Simple;
		#my $data = $xml->XMLin($xmlFiles[0]);
		#my $ref = $data->{OverallSamples}{SummarizedSampleStatistics};
		#my @array = @$ref;
		foreach my $ref (@array) {
			my %hash = %$ref;
			#if ($hash{SampleNumber} eq $sampleNumber && $hash{SampleName} =~ /$sampleName/i) {
			if ($hash{SampleNumber} eq $sampleNumber) {
				$hashOut{$sampleNumber}{clustersRaw} = $hash{NumberOfClustersRaw};
				$hashOut{$sampleNumber}{clustersPF} = $hash{NumberOfClustersPF};
				#print "$hash{SampleNumber},$hash{SampleName},$hash{NumberOfClustersRaw},$hash{NumberOfClustersPF}\n";
				last;
			}
			else {
				$hashOut{$sampleNumber}{clustersRaw} = "NA";
				$hashOut{$sampleNumber}{clustersPF} = "NA";
			}
		}
	});
	
	return \%hashOut;
}

sub my_complex_sort {
  # code that compares $a and $b and returns -1, 0 or 1 as appropriate
  # It's probably best in most cases to do the actual comparison using cmp or <=>

  # expected input format is: SampleNumber_Sequence
  my @aArray = split("_",$a);
  my @bArray = split("_",$b);

  # Extract the digits before the underscore
  my $number_a = $aArray[0];
  my $number_b = $bArray[0];
  
  # extract 2nd set of digits
  my $number_a2 = $aArray[1];
  my $number_b2 = $bArray[1];

  # Extract the string following those digits
  my $letter_a = $aArray[2];
  my $letter_b = $bArray[2];

  # Compare and return
  return $number_a <=> $number_b || $number_a2 <=> $number_b2 || $letter_a cmp $letter_b;
}

sub getRunId {
	my $path = shift;
	if ($path =~ /Data\/Intensities\/BaseCalls/i) {
		my @s = splitdir($path);
		$inputs{runid} = $s[-4];
	}
	else {
		die "ERROR: --basecallsDir option must provide full path to /Data/Intensities/BaseCalls folder\n";
	}
}

sub getDateTimeStamp {
	#return a scalar in the format of "20120928_0835"
    my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst)=localtime(time);
    my $nice_timestamp = sprintf ("%04d%02d%02d_%02d%02d",$year+1900,$mon+1,$mday,$hour,$min);
    return $nice_timestamp;
}
		



sub Usage {
	print "Usage: perl generate_RAWCOUNTS_SGE.pl --basecallsDir /path/to/run/Data/Intensities/BaseCalls --samplesheet /path/to/SampleSheet.csv --config /path/to/config.ini [--sge flag to use SGE scheduler] [--force force overwrite of output directory] [--help] [--tool] [--environment]\n";
}
