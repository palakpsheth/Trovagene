#!/usr/bin/perl

## Usage: perl generate_RAWCOUNTS_singleFastq.pl --fastq /Data/Intensities/BaseCalls/input.fastq --outdir /path/to/outfolder --tempdir /path/to/outfolder/temp --cpus cpus/jobs --Qmin minQscore N --MAPQmin N --mismatch 0.N --percentBases N --bwaMaxGaps N --bwaMaxGapExts N --bwaGapOpenPen N --bwaGapExtPen N --bwaMismatchPen N --ref reference fasta --assay sample assay --input input volume 10/60 --source sample source P/U --mtCoordsFile mutant coordinates file --adaptersFile adapter seqs to trim --primersFile seqs to flag primer-dimers --targetsFile assay targets file [--sge flag to use SGE scheduler] [--sgeQ SGE queue to submit to] [--sgePE SGE parallel environment name] --runId runId of run [[--mode 1/2]] [--keepTemp] [--noTrimming] [--Nmask] [--minlen minimum read length after trimming] [--overlap minimum number of bases to trim] [--clustersRaw] [--clustersPF] [--type] [--tool] [--samplePlate] [--sampleWell] [--i7IndexID] [--index] [--standardGroup] [--batch] [--checkoutNumber] [--ngPerRxn] [--phixFraction] [--projectVersion] --CUTADAPT --FASTQ_QUAL_FILTER --BWA --SAMTOOLS --BAMREADCOUNT --FASTQC --IGVLIB --IGV --BAMSTATS [--environment] --force [--outputBAMSTATS] --MAXSLEEPDELAY

use strict;
use warnings;
$|++;
use File::Basename;
use Cwd qw(abs_path cwd);
my $scriptDir = "";
BEGIN {
	use File::Spec::Functions qw(rel2abs canonpath catdir catfile curdir updir splitpath splitdir catpath);
	$scriptDir = rel2abs($0);
	$scriptDir = dirname($0);
	unshift @INC, "$scriptDir";
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
	$scriptDir = dirname($0);
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
use IPC::Open3;
use Sys::Hostname;
use Try::Tiny;

print "\n";
print qx/ps -o args $$/;
print "\n\n";

my $hostname = hostname;
print "HOSTNAME: $hostname\n";
my $user = $ENV{LOGNAME} || $ENV{USERNAME} || $ENV{USER} || getpwuid( $< );
print "USERNAME: $user\n";

#foreach (@INC) {
	#my $path = $_;
	#if (-e "$path/Schedule/SGELK.pm") {
		#print "FOUND: $path/Schedule/SGELK.pm\n\n";
	#}
#}

my $dtStart = DateTime->now;

## Usage: perl generate_RAWCOUNTS_singleFastq.pl --fastq /Data/Intensities/BaseCalls/input.fastq --outdir /path/to/outfolder --tempdir /path/to/outfolder/temp --cpus cpus/jobs --Qmin minQscore N --MAPQmin N --mismatch 0.N --percentBases N --bwaMaxGaps N --bwaMaxGapExts N --bwaGapOpenPen N --bwaGapExtPen N --bwaMismatchPen N --ref reference fasta --assay sample assay --input input volume 10/60 --source sample source P/U --mtCoordsFile mutant coordinates file --adaptersFile adapter seqs to trim --primersFile seqs to flag primer-dimers --targetsFile assay targets file [--sge flag to use SGE scheduler] [--sgeQ SGE queue to submit to] [--sgePE SGE parallel environment name] --runId runId of run [[--mode 1/2]]  [--keepTemp] [--noTrimming] [--Nmask] [--minlen minimum read length after trimming] [--overlap minimum number of bases to trim] [--clustersRaw] [--clustersPF] [--type] [--tool] [--samplePlate] [--sampleWell] [--i7IndexID] [--index] [--standardGroup] [--batch] [--checkoutNumber] [--ngPerRxn] [--phixFraction] [--projectVersion] --CUTADAPT --FASTQ_QUAL_FILTER --BWA --SAMTOOLS --BAMREADCOUNT --FASTQC --IGVLIB --IGV --BAMSTATS [--environment] --force --MAXSLEEPDELAY
my %inputs = (); 
GetOptions( \%inputs, 'help|h', 'fastq:s', 'outdir:s', 'tempdir:s', 'cpus:i', 'Qmin:i', 'MAPQmin:i', 'mismatch:f', 'percentBases:i', 'bwaMaxGaps:i', 'bwaMaxGapExts:i', 'bwaGapOpenPen:i', 'bwaGapExtPen:i', 'bwaMismatchPen:i', 'ref:s', 'assay:s', 'input:s', 'source:s', 'mtCoordsFile:s', 'adaptersFile:s', 'primersFile:s', 'targetsFile:s', 'sge', 'sgeQ:s', 'runId:s', 'sgePE:s','mode:i','keepTemp', 'noTrimming', 'Nmask','minlen:i','overlap:i', 'clustersRaw:s', 'clustersPF:s', 'type:s', 'tool:s', 'samplePlate:s', 'sampleWell:s', 'i7IndexID:s', 'index:s', 'standardGroup:s', 'batch:s', 'checkoutNumber:s', 'ngPerRxn:s', 'phixFraction:s', 'projectVersion:s','CUTADAPT:s','FASTQ_QUAL_FILTER:s','BWA:s','SAMTOOLS:s','BAMREADCOUNT:s','FASTQC:s','IGVLIB:s','IGV:s','BAMSTATS:s', 'environment:s', 'force|f', 'outputBAMSTATS', 'IGVSERVER:s', 'MAXSLEEPDELAY:i'); 

# if help is requested
if ($inputs{help}) {
	Usage();
	exit 0;
}

foreach my $key ('fastq', 'outdir', 'cpus', 'Qmin', 'MAPQmin', 'mismatch', 'percentBases', 'bwaMaxGaps', 'bwaMaxGapExts', 'bwaGapOpenPen', 'bwaGapExtPen', 'bwaMismatchPen', 'ref', 'assay', 'input', 'source', 'mtCoordsFile', 'adaptersFile', 'primersFile', 'targetsFile', 'runId', 'tempdir','minlen','overlap', 'clustersRaw', 'clustersPF', 'type', 'tool', 'samplePlate', 'sampleWell', 'i7IndexID', 'index', 'standardGroup', 'batch', 'checkoutNumber', 'ngPerRxn', 'phixFraction', 'projectVersion','CUTADAPT','FASTQ_QUAL_FILTER','BWA','SAMTOOLS','BAMREADCOUNT','FASTQC','IGVLIB','IGV','BAMSTATS') {
	if (!defined $inputs{$key} || !exists $inputs{$key}) {
		Usage();
		die "ERROR: Undefined input field $key found!\n";
	}
}

if (!defined $inputs{mode}) {
	$inputs{mode} = 1;
}

# figure out base directory from current dir ../scripts/readsProcessing
my $baseDir = $scriptDir;
my @dirs = splitdir($baseDir);
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
}

## predefined paths for programs and files
my %paths;
# programs
if (defined $inputs{CUTADAPT} && -e $inputs{CUTADAPT}) {
	$paths{CUTADAPT} = rel2abs($inputs{CUTADAPT}); 
}
else {
	$paths{CUTADAPT} = catfile($baseDir,"bin","cutadapt_wrapper");
}
if (defined $inputs{FASTQ_QUAL_FILTER} && -e $inputs{FASTQ_QUAL_FILTER}) {
	$paths{FASTQ_QUAL_FILTER} = rel2abs($inputs{FASTQ_QUAL_FILTER}); 
}
else {
	$paths{FASTQ_QUAL_FILTER} = catfile($baseDir,"bin","fastq_quality_filter");
}
if (defined $inputs{BWA} && -e $inputs{BWA}) {
	$paths{BWA} = rel2abs($inputs{BWA}); 
}
else {
	$paths{BWA} = catfile($baseDir,"bin","bwa-0.7.12","bwa");
}
if (defined $inputs{SAMTOOLS} && -e $inputs{SAMTOOLS}) {
	$paths{SAMTOOLS} = rel2abs($inputs{SAMTOOLS}); 
}
else {
	$paths{SAMTOOLS} = catfile($baseDir,"bin","samtools-1.3.1","samtools");
}
if (defined $inputs{BAMREADCOUNT} && -e $inputs{BAMREADCOUNT}) {
	$paths{BAMREADCOUNT} = rel2abs($inputs{BAMREADCOUNT}); 
}
else {
	$paths{BAMREADCOUNT} = catfile($baseDir,"bin","bam-readcount");
}
if (defined $inputs{FASTQC} && -e $inputs{FASTQC}) {
	$paths{FASTQC} = rel2abs($inputs{FASTQC}); 
}
else {
	$paths{FASTQC} = catfile($baseDir,"bin","FastQC","fastqc");
}
if (defined $inputs{IGV} && -e $inputs{IGV}) {
	$paths{IGV} = rel2abs($inputs{IGV}); 
}
else {
	$paths{IGV} = catfile($baseDir,"bin","IGV_2.3.79","igv.sh");
}
if (defined $inputs{BAMSTATS} && -e $inputs{BAMSTATS}) {
	$paths{BAMSTATS} = rel2abs($inputs{BAMSTATS}); 
}
else {
	$paths{BAMSTATS} = catfile($baseDir,"bin","BAMStats-1.25","BAMStats-1.25.jar");
}
# scripts
$paths{NMASK} = catfile($baseDir,"scripts","readsProcessing","subN_v_0.1.0.pl");
if (defined $inputs{IGVLIB} && -e $inputs{IGVLIB}) {
	$paths{IGVLIB} = rel2abs($inputs{IGVLIB}); 
}
else {
	$paths{IGVLIB} = catfile($baseDir,"scripts","readsProcessing","igvlib.pl");
}
# files
if (defined $inputs{ref} && -e $inputs{ref}) {
	$paths{REF} = rel2abs($inputs{'ref'}); 
}
else {
	$paths{REF} = catfile($baseDir,"ref","hg19","hg19_primary_chromosomes.fa"); 
}
if (defined $inputs{adaptersFile} && -e $inputs{adaptersFile}) {
	$paths{adaptersFile} = rel2abs($inputs{'adaptersFile'}); 
}
else {
	$paths{adaptersFile} = catfile($baseDir,"data","trovSeqsToTrim.txt"); 
}
if (defined $inputs{primersFile} && -e $inputs{primersFile}) {
	$paths{primersFile} = rel2abs($inputs{'primersFile'}); 
}
else {
	$paths{primersFile} = catfile($baseDir,"data","trovPrimersToFlag.txt"); 
}
if (defined $inputs{targetsFile} && -e $inputs{targetsFile}) {
	$paths{targetsFile} = rel2abs($inputs{'targetsFile'}); 
}
else {
	$paths{targetsFile} = catfile($baseDir,"data","trovTargetedRegions.bed"); 
}
# make sure all paths files exist
foreach my $key (sort keys %paths) {
	$paths{$key} = rel2abs($paths{$key});
	if (!-e $paths{$key}) {
		die "ERROR: $key not found at $paths{$key}: $!\n";
	}
}

# if force then its the 2nd time its running. lets double the cores allocated to be safe up to max of 32
if (defined $inputs{force}) {
	if ($inputs{force} && int($inputs{cpus}) <= 16){ 
		$inputs{cpus} = int($inputs{cpus}) * 2;
	}
}

# sleep delay
my $MAXSLEEPDELAY=30;
if (defined $inputs{'MAXSLEEPDELAY'}) {
	$MAXSLEEPDELAY = int($inputs{'MAXSLEEPDELAY'});
}


### global variables
# initialize cacheOutHash
my %cacheOutHash;
my %mutCoordsCount;

# runFolder
my @s = split("/Data/Intensities/BaseCalls/", $inputs{fastq});
my $runFolder = $s[0];

### DO STUFF ###

# check file integrity
verifyFastqGzIntegrity( $inputs{fastq} );

# set up variables IF SGE
my $sge;
if ($inputs{sge}) {
	if (defined $inputs{sgeQ} && exists $inputs{sgeQ} && defined $inputs{sgePE} && exists $inputs{sgePE}) {
		print "Using SGE queue: $inputs{sgeQ} and parallel environment: $inputs{sgePE}\n";
	}
	else {
		print "WARNING: When using --sge, --sgeQ AND --sgePE should be defined! Using default values...\n";
		#$inputs{sgeQ} = "all.q";
		$inputs{sgeQ} = "amd.q";
		$inputs{sgePE} = "pe1";
		#$sge=Schedule::SGELK->new(verbose=>1,queue=>"testq",pe=>"pe1",numcpus=>"$inputs{cpus}",workingdir=>"$inputs{tempDir}",waitForEachJobToStart=>0,qsubxopts=>"-l mem_free=4G");		
	}
	$sge=Schedule::SGELK->new(verbose=>1,queue=>"$inputs{sgeQ}",pe=>"$inputs{sgePE}",numcpus=>"$inputs{cpus}",workingdir=>"$inputs{tempdir}",waitForEachJobToStart=>0,qsubxopts=>"-l mem_free=4G");
}			

# get filename
my $fastqOrig = $inputs{fastq};
my $name = basename($fastqOrig,".fastq.gz");

# set up log file for sample
my $log_file = catfile($inputs{outDir},"$name","_log.txt");
tee(STDOUT, '>>', "$log_file");
tee(STDERR, '>>', "$log_file");
	
my ($sampleName, $sampleNumber) = getFastqInfo($name);
	
## get target info based on sampleNumber
my $assay = $inputs{'assay'};
my $input = $inputs{'input'};
my $source = $inputs{'source'};
my $stdgrp = $inputs{'standardGroup'};

# load targets file
my $targetsRef = loadTargetsFile($inputs{'targetsFile'});
my @targets = @$targetsRef;
	
# get target based on assay
my ($target, $wtSeq) = getTargetFromAssay($assay);
@s = split(/:/,$target);
my @t = split(/-/,$s[1]);
my $targetChr = $s[0];
my $targetStart = $t[0];
my $targetEnd = $t[1];
	
# load mutants based on assay and target
# load mtCoordsFile
my $mutantCoordsRef = loadMutantsCoordsFile($inputs{'mtCoordsFile'});
my @mutantsCoordsArr = @$mutantCoordsRef;

print "Processing sample: $name\n";	
print "\n";
my $fastq = $fastqOrig;
	
# find expected CN from name if possible
my $expectedCN = "";
if ($name =~ m/^(STD|AV|REF|STx)/i) {
	$expectedCN = $sampleName;
	my @s = split("-",$expectedCN);
	$expectedCN = $s[0];
	$expectedCN =~ s/\D+//g;
}
elsif ($name =~ m/-STD/i) {
	$expectedCN = $sampleName;
	my @s = split("-",$expectedCN);
	$expectedCN = $s[1];
	$expectedCN =~ s/\D+//g;
}
elsif ($name =~ m/-CTL/i) {
	$expectedCN = $sampleName;
	my @s = split("-",$expectedCN);
	$expectedCN = $s[1];
	$expectedCN =~ s/\D+//g;
	if ($name =~ m/CTLn/i) {
		$expectedCN = 0;
	}
}
elsif ($name =~ m/CTLn/i) {
	$expectedCN = $sampleName;
	#my @s = split("-",$expectedCN);
	$expectedCN = 0;
	#$expectedCN =~ s/\D+//g;
}
elsif ($name =~ m/(^CTL)/i) {
	if ($name =~ m/(CTLn)/i) {
		$expectedCN = 0;
	}
	else {
		$expectedCN = $sampleName;
		my @s = split("-",$expectedCN);
		$expectedCN = $s[0];
		$expectedCN =~ s/\D+//g;
	}
}
elsif ($name =~ m/(NTC)/i) {
	$expectedCN = 0;
}
elsif ($name =~ m/^(\d+)MT/i) {
	$expectedCN = $sampleName;
	my @s = split("-",$expectedCN);
	$expectedCN = $s[0];
	$expectedCN =~ s/\D+//g;
}
	
# count raw reads in fastq
my $rawReads = 0;
my $CMD = "zcat $fastq | wc -l";
print "Running command: $CMD\n";
$rawReads = qx($CMD);
if ($? == -1) {
    print "ERROR: Failed to execute: $!\n";
}
elsif ($? & 127) {
    printf "ERROR: Child $! died with signal %d, %s coredump\n",
    ($? & 127),  ($? & 128) ? 'with' : 'without';
}
#my @s = split(/\s+/, $rawReads);
$rawReads = int($rawReads/4); # each fastq record is 4 lines
print "Raw Reads: $rawReads\n";
print "\n";

my $fastqTrim = basename($fastq);
my $replace = "_trimmed_minQ".$inputs{Qmin}.".fastq.gz";
if ($inputs{Nmask} || ($inputs{percentBases} == -1 && $inputs{Qmin} >= 0)) {
	$replace = "_trimmed_minQ".$inputs{Qmin}."masked.fastq.gz";
}

$fastq = catfile($inputs{tempdir},$fastqTrim);
$fastq =~ s/.fastq.gz/_trimmed.fastq.gz/;
$fastqTrim = $fastq;
$fastqTrim =~ s/_trimmed.fastq.gz/$replace/;

# trim adapters	
if ($inputs{noTrimming} || $inputs{mismatch} == -1) {
	print "--noTrimming or mismatch=-1 specified...\nSkipping adapter trimming.\n\n";
	copy "$fastqOrig","$fastq";
}
else {
	# cutadapt -a ADAPTER [options] [-o output.fastq] input.fastq
	$CMD = "$paths{CUTADAPT} -m $inputs{minlen} -O $inputs{overlap} -e $inputs{mismatch} -n 2 -b file:$paths{adaptersFile} -o $fastq $fastqOrig";
	print "Running command: $CMD\n";
	system($CMD);
	print "\n";
}
if ($? == -1) {
    die "ERROR: failed to execute: $!\n";
}
elsif ($? & 127) {
    die( sprintf "ERROR: Child $! died with signal %d, %s coredump\n", ($? & 127),  ($? & 128) ? 'with' : 'without');
}
else {
	if ( !-e $fastq || !verifyFastqGzIntegrity_returnCode($fastq) ) {
		my $secCount=0;
		while ( (!-e $fastq || !verifyFastqGzIntegrity_returnCode($fastq)) && $secCount<$MAXSLEEPDELAY ) {
			$secCount++;
			sleep 1;
		}
		print "Total sleep time: $secCount\n";
	}
}
	
# count reads in trimmed-only fastq
my $trimmedReads = 0;
$CMD = "zcat $fastq | wc -l";
print "Running command: $CMD\n";
$trimmedReads = qx($CMD);
$trimmedReads = int($trimmedReads/4); # each fastq record is 4 lines
print "Total Reads in trimmed FASTQ: $trimmedReads\n";
print "\n";

# filter trimmed reads based on basecall Qscore
if ($inputs{Nmask} || ($inputs{percentBases} == -1 && $inputs{Qmin} >= 0)) {
	$CMD = "perl $paths{NMASK} -i $fastq -o $fastqTrim -q $inputs{Qmin}";
	print "Running command: $CMD\n";
	system($CMD);
	print "\n";
}
elsif ($inputs{percentBases} != -1 && $inputs{Qmin} != -1) {
	#filter out reads with N percent bases qscore less than Qmin
	#usage: fastq_quality_filter [-h] [-v] [-q N] [-p N] [-z] [-i INFILE] [-o OUTFILE]
	$CMD = "zcat $fastq | $paths{FASTQ_QUAL_FILTER} -Q33 -v -q $inputs{Qmin} -p $inputs{percentBases} -z -o $fastqTrim";
	print "Running command: $CMD\n";
	system($CMD);
	print "\n";
}
elsif ($inputs{percentBases} == -1 && $inputs{Qmin} == -1) {
	print "Skipping quality score filtering and/or masking...\n\n";
	copy "$fastq","$fastqTrim";
}
$fastq = $fastqTrim;
if ($? == -1) {
    die "ERROR: failed to execute: $!\n";
}
elsif ($? & 127) {
    die( sprintf "ERROR: Child $! died with signal %d, %s coredump\n", ($? & 127),  ($? & 128) ? 'with' : 'without' );
}
else {
	if ( !-e $fastq || !verifyFastqGzIntegrity_returnCode($fastq) ) {
		my $secCount=0;
		while ( (!-e $fastq || !verifyFastqGzIntegrity_returnCode($fastq)) && $secCount<$MAXSLEEPDELAY ) {
			$secCount++;
			sleep 1;
		}
		print "Total sleep time: $secCount\n";
	}
}
	
# count reads in filtered trimmed fastq
my $totalReads = 0;
$CMD = "zcat $fastq | wc -l";
print "Running command: $CMD\n";
$totalReads = qx($CMD);
$totalReads = int($totalReads/4); # each fastq record is 4 lines
print "Total Reads in trimmed filtered FASTQ: $totalReads\n";
print "\n";

### perfrom alignments ###
# bwa aln [-n maxDiff] [-o maxGapO] [-e maxGapE] [-d nDelTail] [-i nIndelEnd] [-k maxSeedDiff] [-l seedLen] [-t nThrds] [-cRN] [-M misMsc] [-O gapOsc] [-E gapEsc] [-q trimQual] <in.db.fasta> <in.query.fq> > <out.sai>
# if assay is deletion assay, then run different BWA parameters
#'bwaMaxGaps:i', 'bwaMaxGapExts:i', 'bwaGapOpenPen:i', 'bwaGapExtPen:i', 'bwaMismatchPen:i'

if ($inputs{mode} == 1) {
	if ($assay =~ m/del/i) {
		$CMD = "$paths{BWA} aln -o $inputs{bwaMaxGaps} -e $inputs{bwaMaxGapExts} -O $inputs{bwaGapOpenPen} -E $inputs{bwaGapExtPen} -l 100 -k 30 -M 1 -d 2 -i 2 -t $inputs{cpus} $inputs{ref}";
	}
	else {
		$CMD = "$paths{BWA} aln -l 100 -k 3 -M $inputs{bwaMismatchPen} -t $inputs{cpus} $inputs{ref}";
	}
}
elsif ($inputs{mode} == 2) {
	$CMD = "$paths{BWA} aln -M $inputs{bwaMismatchPen} -t $inputs{cpus} $inputs{ref}";
}

my $outfile = catfile($inputs{tempdir},"$name.sai");
$CMD = $CMD." $fastq > $outfile";
print "Running command: $CMD\n";
#print "\n";
#IF SGE
if ($inputs{sge}) {
	my $jname = $name;
	#$jname =~ s/^[0-9]+//ig;
	#$jname =~ s/^-+//ig;
	#$jname =~ s/^_+//ig;
	$sge->set("jobname",($jname."_BWA"));
	$sge->set("seed",$sampleNumber);
	$CMD = "/usr/bin/time -v " . $CMD;
	$sge->pleaseExecute_andWait("$CMD");
	sleep(5);
}
else {
	system($CMD);
	sleep 10;
}
print "\n";
	
# bwa samse [-n maxOcc] <in.db.fasta> <in.sai> <in.fq> > <out.sam>
my $infile = $outfile;
$outfile =~ s/.sai/.sam/i;
$CMD = "$paths{BWA} samse $inputs{ref} $infile $fastq > $outfile";
print "Running command: $CMD\n";
system($CMD);
if ($? == -1) {
    die "ERROR: failed to execute: $!\n";
}
elsif ($? & 127) {
    die( sprintf "ERROR: Child $! died with signal %d, %s coredump\n", ($? & 127),  ($? & 128) ? 'with' : 'without' );
}
else {
	if ( !-e $outfile ) {
		my $secCount=0;
		while ( !-e $outfile && $secCount<$MAXSLEEPDELAY ) {
			$secCount++;
			sleep 1;
		}
		print "Total sleep time: $secCount\n";
	}
}
print "\n";
	
# extract unmapped reads
$infile = $outfile;
#$outfile =~ s/.sam/.unmapped.bam/i;
$outfile = catfile($inputs{outdir},"$name.unmapped.bam");
$CMD = "$paths{SAMTOOLS} view -b -f 4 $infile > $outfile";
print "Running command: $CMD\n";
system($CMD);
sleep 10;
print "\n";

# run FASTQC on unmapped reads
$CMD = "$paths{FASTQC} --noextract -t $inputs{cpus} $outfile";
print "Running command: $CMD\n";
#IF SGE
if ($inputs{sge}) {
	my $jname = $name;
	#$jname =~ s/^[0-9]+//ig;
	#$jname =~ s/^-+//ig;
	#$jname =~ s/^_+//ig;
	$sge->set("jobname",($jname."_FASTQC"));
	$sge->set("seed",$sampleNumber);
	$CMD = "/usr/bin/time -v " . $CMD;
	$sge->pleaseExecute_andWait("$CMD");
	sleep(5);
}
else {
	system($CMD);
	sleep 10;
}
print "\n";
	
# analyze unmapped reads to count primer-dimers
$CMD = "$paths{SAMTOOLS} view $outfile";
print "Running command: $CMD\n";
my @unmappedReadsSam = qx($CMD);
chomp @unmappedReadsSam;
my $primerDimerCount = countPrimerDimers(\@unmappedReadsSam,$inputs{primersFile},$assay);
print "Total primer-artifacts found in unmapped reads: $primerDimerCount\n";
print "\n";
	
# filter alignments and keep only primary alignments
# samtools view -bSu out.sam  | samtools sort -  out.sorted
$outfile =~ s/.unmapped.bam/.sorted.bam/i;
$CMD = "$paths{SAMTOOLS} view -F 256 -q $inputs{MAPQmin} -bSu $infile | $paths{SAMTOOLS} sort --threads $inputs{cpus} -o $outfile -";
print "Running command: $CMD\n";
#IF SGE
if ($inputs{sge}) {
	my $jname = $name;
	#$jname =~ s/^[0-9]+//ig;
	#$jname =~ s/^-+//ig;
	#$jname =~ s/^_+//ig;
	$sge->set("jobname",($jname."_SAMTOOLS"));
	$sge->set("seed",$sampleNumber);
	$CMD = "/usr/bin/time -v " . $CMD;
	$sge->pleaseExecute_andWait("$CMD");
	sleep(5);
}
else {
	system($CMD);
	sleep 10;
}
print "\n";

# run FASTQC on mapped reads
$CMD = "$paths{FASTQC} --noextract -t $inputs{cpus} $outfile";
print "Running command: $CMD\n";
#IF SGE
if ($inputs{sge}) {
	my $jname = $name;
	#$jname =~ s/^[0-9]+//ig;
	#$jname =~ s/^-+//ig;
	#$jname =~ s/^_+//ig;
	$sge->set("jobname",($jname."_FASTQC"));
	$sge->set("seed",$sampleNumber);
	$CMD = "/usr/bin/time -v " . $CMD;
	$sge->pleaseExecute_andWait("$CMD");
	sleep(5);
}
else {
	system($CMD);
	sleep 10;
}
print "\n";
	
# index BAM file
#samtools index test_sorted.bam test_sorted.bai
$infile = $outfile;
$outfile =~ s/.sorted.bam/.sorted.bai/i;
$CMD = "$paths{SAMTOOLS} index $infile $outfile";
print "Running command: $CMD\n";
system($CMD);
if ($? == -1) {
    die "ERROR: failed to execute: $!\n";
}
elsif ($? & 127) {
    die( sprintf "ERROR: Child $! died with signal %d, %s coredump\n", ($? & 127),  ($? & 128) ? 'with' : 'without' );
}
else {
	if ( !-e $outfile ) {
		my $secCount=0;
		while ( !-e $outfile && $secCount<$MAXSLEEPDELAY ) {
			$secCount++;
			sleep 1;
		}
		print "Total sleep time: $secCount\n";
	}
}
print "\n";

my $finalBAM = $infile;
	
# mapped reads
$CMD = "$paths{SAMTOOLS} view -F 4 $infile | wc -l";
print "Running command: $CMD\n";
my $mappedReads = qx($CMD);
#@s = split(/\s+/, $mappedReads);
$mappedReads = int($mappedReads);
print "Mapped Reads: $mappedReads\n";
print "\n";

# PhiX reads
$CMD = "$paths{SAMTOOLS} view -F 4 $infile PhiX | wc -l";
print "Running command: $CMD\n";
my $phixReads = qx($CMD);
$phixReads = int($phixReads);
print "PhiX Reads: $phixReads\n";
print "\n";
	
# target reads (gene_seq)
my $targetReads = -1;
my @targetReadsSam;
if ($inputs{mode} == 1) {
	$CMD = "$paths{SAMTOOLS} view -F 4 $infile $target";
	print "Running command: $CMD\n";
	@targetReadsSam = qx($CMD);
	chomp @targetReadsSam;
	$targetReads = scalar(@targetReadsSam);
}
elsif ($inputs{mode} == 2) {
	$targetReads = int($mappedReads) - int($phixReads);
	$CMD = "$paths{SAMTOOLS} view -F 4 $infile";
	print "Running command: $CMD\n";
	@targetReadsSam = qx($CMD);
	chomp @targetReadsSam;
}
print "Target Reads: $targetReads\n";
print "\n";


##### COUNT WT AND MT READS #####
	
### count target region wild type reads if target region is more than just a SNP
my $wtReads = 0;
if ($inputs{mode} == 1) {  ### IF COUNT MODE = 1
	if ($targetStart != $targetEnd) {
		if ($assay =~ /del/i) { # only if deletion asssay, count WT reads as those without any deletions >1
			foreach my $samLine (@targetReadsSam) {
				chomp($samLine);
				#M03685:22:000000000-AEN0T:1:2113:5528:8081      0       chr7    55242447        37      57M     *       0       0       AATTCCCGTCGCTATCAAGGAATTAAGAGAAGCAACATCTCCGAAAGCCAACAAGGA       CCCCCGGGGGGGGGGGGGGG?FGEFFCCFGGGGGGGCEFGFGGGEGCFEGFFCDC<<        XT:A:U  NM:i:0  X0:i:1  X1:i:0  XM:i:0  XO:i:0  XG:i:0  MD:Z:57
				my @s = split("\t",$samLine);
				#chomp($s[9]);
				#if (index($s[9],$wtSeq,0) != -1) {
				#	$wtReads++;
				#}
				chomp($s[16]);
				my @open = split(":",$s[16]);
				chomp($s[17]);
				my @ext = split(":",$s[17]);
				if (($open[-1] <= 1) && ($ext[-1] <= 1)) {
					$wtReads++;
				}
			}
		}
		else { # otherwise if multi-SNP assay, count WT as the exact sequence across target region
			foreach my $samLine (@targetReadsSam) {
				chomp($samLine);
				#M03685:22:000000000-AEN0T:1:2113:5528:8081      0       chr7    55242447        37      57M     *       0       0       AATTCCCGTCGCTATCAAGGAATTAAGAGAAGCAACATCTCCGAAAGCCAACAAGGA       CCCCCGGGGGGGGGGGGGGG?FGEFFCCFGGGGGGGCEFGFGGGEGCFEGFFCDC<<        XT:A:U  NM:i:0  X0:i:1  X1:i:0  XM:i:0  XO:i:0  XG:i:0  MD:Z:57
				my @s = split("\t",$samLine);
				chomp($s[9]);
				if (index($s[9],$wtSeq,0) != -1) {
					$wtReads++;
				}
			}
		}
		print "WildType Target Region Reads: $wtReads\n";
	}
}
elsif ($inputs{mode} == 2) {   ### IF COUNT MODE = 2
	$CMD = "$paths{SAMTOOLS} view -F 4 $infile WT | wc -l";
	print "Running command: $CMD\n";
	$wtReads = qx($CMD);
	$wtReads = int($wtReads);
	print "WildType Reads: $wtReads\n";
	print "\n";
}
print "\n";
if ($wtReads == 0) { $wtReads = "NA"; }

##### COUNT MUTANTS BASED ON COUNT MODE OPTION #####
if ($inputs{mode} == 1) {
	print "\n### FINDING MUTANT COUNTS BASED ON ALIGNMENT PILEUP ###\n\n";
	# get pileup info based on assay targets
	$CMD = "$paths{BAMREADCOUNT} -f $inputs{ref} -l $inputs{mtCoordsFile} $infile";
	print "Running command: $CMD\n";
	my @readCounts = qx($CMD);
	chomp(@readCounts);
	print "\n";
		
	# process read count pileup based on each mutant entry
	# IF DEL assay
	if ($assay =~ m/del/i) {
		foreach my $mutantCoordsLine (@mutantsCoordsArr) {
			#chr	start	end	seq	type	name	cosmicID
			my @mut = split("\t",$mutantCoordsLine);
			chomp(@mut);
			$mutCoordsCount{$mut[1]}{$mut[3]} = 0;
			foreach my $readCount (@readCounts) {
				chomp($readCount);
				#chr12	25398281	C	1795744	=...	A:154:25.86:30.36:25.86:0:154:0.87:0.06:63.95:0:0.00:31.00:0.42	C:1623256:36.77:37.61:36.77:0:1623256:0.87:0.03:37.64:0:0.00:31.00:0.42	G:47:31.64:30.87:31.64:0:47:0.87:0.05:46.68:0:0.00:31.00:0.42	T:172236:36.67:36.80:36.67:0:172236:0.87:0.03:37.64:0:0.00:31.00:0.42	N:0:0.00:0.00:0.00:0:0:0.00:0.00:0.00:0:0.00:0.00:0.00	-C:50:37.00:0.00:37.00:0:50:0.80:0.07:37.84:0:0.00:30.00:0.40	-CC:1:37.00:0.00:37.00:0:1:0.86:0.07:0.00:0:0.00:29.00:0.41
				my @read = split("\t",$readCount);
				if ($mut[0] =~ m/$read[0]/ && $mut[1] =~ m/$read[1]/) {
					my %countsHash;
					$countsHash{$mut[3]} = 0;
					for (my $i = 5; $i<(scalar(@read)); $i++) {
						my $line = $read[$i];
						chomp($line);
						my @s = split(':',$line);
						$countsHash{$s[0]} = $s[1];
					}
					$mutCoordsCount{$mut[1]}{$mut[3]} = int($countsHash{$mut[3]});
					last;
				}
			}
		}
	}
	# ELSE SNP ASSAY
	else {
		my @nucs = ("A","C","T","G","N");
		foreach my $mutantCoordsLine (@mutantsCoordsArr) {
			#chr	start	end	name
			my @mut = split("\t",$mutantCoordsLine);
			chomp(@mut);
			#$mutCoordsCount{$mut[3]} = 0;
			foreach my $nuc (@nucs) {
				$mutCoordsCount{$mut[1]}{$nuc} = 0;
			}
			foreach my $readCount (@readCounts) {
				chomp($readCount);
				#chr12	25398281	C	1795744	=...	A:154:25.86:30.36:25.86:0:154:0.87:0.06:63.95:0:0.00:31.00:0.42	C:1623256:36.77:37.61:36.77:0:1623256:0.87:0.03:37.64:0:0.00:31.00:0.42	G:47:31.64:30.87:31.64:0:47:0.87:0.05:46.68:0:0.00:31.00:0.42	T:172236:36.67:36.80:36.67:0:172236:0.87:0.03:37.64:0:0.00:31.00:0.42	N:0:0.00:0.00:0.00:0:0:0.00:0.00:0.00:0:0.00:0.00:0.00	-C:50:37.00:0.00:37.00:0:50:0.80:0.07:37.84:0:0.00:30.00:0.40	-CC:1:37.00:0.00:37.00:0:1:0.86:0.07:0.00:0:0.00:29.00:0.41
				my @read = split("\t",$readCount);
				if ($mut[0] =~ m/$read[0]/ && $mut[1] =~ m/$read[1]/) {
					my %countsHash;
					foreach my $nuc (@nucs) {
						$countsHash{$nuc} = 0;
					}
					for (my $i = 5; $i<(scalar(@read)); $i++) {
						my $line = $read[$i];
						chomp($line);
						my @s = split(':',$line);
						$countsHash{$s[0]} = $s[1];
					}
					foreach my $nuc (@nucs) {
						$mutCoordsCount{$mut[1]}{$nuc} = $countsHash{$nuc};
					}
					# SET WT READS FOR NON_KRAS
					if ($targetStart == $targetEnd) {
						$wtReads = $countsHash{$wtSeq};
					}
					last;
				}
			}
		}
	}
}
elsif ($inputs{mode} == 2) {
	print "\n### FINDING MUTANT COUNTS BASED ON ALIGNMENT TO MUTANT-SPECIFIC REFERENCE ###\n\n";
	my %chrCountHash;
	# count number of reads for each "chromosome"
	foreach my $samLine (@targetReadsSam) {
		chomp($samLine);
		#M03685:22:000000000-AEN0T:1:2113:5528:8081      0       chr7    55242447        37      57M     *       0       0       AATTCCCGTCGCTATCAAGGAATTAAGAGAAGCAACATCTCCGAAAGCCAACAAGGA       CCCCCGGGGGGGGGGGGGGG?FGEFFCCFGGGGGGGCEFGFGGGEGCFEGFFCDC<<        XT:A:U  NM:i:0  X0:i:1  X1:i:0  XM:i:0  XO:i:0  XG:i:0  MD:Z:57
		my @s = split("\t",$samLine); chomp(@s);
		if (exists $chrCountHash{$s[2]}) {
			$chrCountHash{$s[2]} = $chrCountHash{$s[2]} + 1;
		}
		else {
			$chrCountHash{$s[2]} = 1;
		}
	}
	# for each "chromosome", generate mutant entry into mutCoordsCount
	foreach my $key (sort keys %chrCountHash) {
		next if $key =~ /(WT|PhiX)/i;
		my @s = split('_',$key); chomp(@s);
		#>chr7_55242465_-GGAATTAAGAGAAGC_c.2235_2249del15
		$mutCoordsCount{$s[1]}{$s[2]} = $chrCountHash{$key};
		print "Chr: $s[0] Start: $s[1] Seq: $s[2] Count: $chrCountHash{$key}\n";  
	}
	print "\n";
}
	
# other and ota counts
my $otherCount = 0;
$otherCount = int($totalReads) - int($mappedReads) - int($primerDimerCount);
if ($otherCount<0) { $otherCount = 0; }
print "Other Reads: $otherCount\n";
my $otaCount = int($mappedReads) - int($targetReads) - int($phixReads);
print "OTA_SUM: $otaCount\n";

#### summary stuff ####
my @mutantLines;
if ($inputs{mode} == 1) {
	foreach my $mutantCoordsLine (@mutantsCoordsArr) {
		#chr	start	end	seq	type	name	cosmicID	cds
		my @mut = split("\t",$mutantCoordsLine);
		chomp(@mut);
		foreach my $seq (sort keys %{ $mutCoordsCount{$mut[1]} }) {
			my $line = "$mut[0],$mut[1],$seq,$mutCoordsCount{$mut[1]}{$seq}";
			push @mutantLines, $line;
		}
	}
}
elsif ($inputs{mode} == 2) {
	foreach my $mutantCoordsLine (@mutantsCoordsArr) {
		#chr	start	end	seq	type	name	cosmicID	cds
		my @mut = split("\t",$mutantCoordsLine);
		chomp(@mut);
		my $line = '';
		if (exists $mutCoordsCount{$mut[1]}{$mut[3]}) {
			$line = "$mut[0],$mut[1],$mut[3],$mutCoordsCount{$mut[1]}{$mut[3]}";
		}
		else {
			$line = "$mut[0],$mut[1],$mut[3],0";
		}
		push @mutantLines, $line;
	}
}

# build and push hash to summary cache array
$inputs{runId} = substr($inputs{runId},0,34);
my %hash = (
	"lineNum" => int($sampleNumber),
	"runId" => $inputs{runId},
	"sampleNumber" => int($sampleNumber),
	"sampleName" => $sampleName,
	"totalReads" => int($totalReads), # total reads after adapter trimming and Qscore filtering
	"trimmedReads" => int($trimmedReads), # total reads after adapter trimming
	"totalSeq" => int($mappedReads), # total mapped reads
	"targetReads" => int($targetReads), # total mapped reads in target region
	#"mutLine" => $mutLine,
	"mutCoordsCountRef" => \%mutCoordsCount,
	"other" => int($otherCount),
	"OTA_SUM" => int($otaCount),
	"rawReads" => int($rawReads),
	"phixReads" => int($phixReads),
	"primerDimerReads" => int($primerDimerCount),
	"targetWtReads" => int($wtReads),
	"expectedCN" => $expectedCN,
	"input" => $input,
	"assay" => $assay,
	"source" => $source,
	"clustersRaw" => $inputs{clustersRaw},
	"clustersPF" => $inputs{clustersPF},
	"type" => $inputs{type},
	"tool" => $inputs{tool},
	"samplePlate" => $inputs{samplePlate},
	"sampleWell" => $inputs{sampleWell},
	"i7IndexID" => $inputs{i7IndexID},
	"index" => $inputs{index},
	"standardGroup" => $inputs{standardGroup},
	"batch" => $inputs{batch},
	"checkoutNumber" => $inputs{checkoutNumber},
	"ngPerRxn" => $inputs{ngPerRxn},
	"phixFraction" => $inputs{phixFraction},
	"projectVersion" => $inputs{projectVersion},
	"environment" => $inputs{environment},
	"runFolder" => $runFolder,
);

### perform count sanity check 
countSanityCheck(\%hash);

# print out sample specific file
$outfile = catfile($inputs{outdir},($name."_".$assay."_".$input."_".$source."_".$stdgrp."_rawCounts.csv"));
#my $outFile = "$outDir/$name"."_rawCounts.csv";
open(OUT, '>', $outfile) or die "ERROR: Could not open file $outfile for printing $!\n";

# HEADER
#print OUT "RunId,SampleNumber,Name,Assay,Input,Source,ExpectedCN,Type,Tool,ClustersRaw,ClustersPF,RawReads,TrimmedReads,TrimmedFilteredReads,TotalMappedReads,TotalTargetReads,PhiXReads,PrimerArtifacts,OTHER,OTA_SUM,TargetWTReads"."$mutHeader\n";
print OUT "RunId,RunFolder,SampleNumber,Name,Assay,Input,Source,ExpectedCN,Type,Tool,Environment,SamplePlate,SampleWell,I7IndexID,Index,StandardGroup,Batch,CheckoutNumber,ngPerRxn,PhixFraction,ProjectVersion,ClustersRaw,ClustersPF,RawReads,TrimmedReads,TrimmedFilteredReads,TotalMappedReads,TotalTargetReads,PhiXReads,PrimerArtifacts,Other,OTA,TargetWTReads,Chr,Start,Sequence,Count\n";

# BODY
#print OUT "$hash{'runId'},$hash{'sampleNumber'},$hash{'sampleName'},$hash{'assay'},$hash{'input'},$hash{'source'},$hash{'expectedCN'},$hash{'type'},$hash{'tool'},$hash{'clustersRaw'},$hash{'clustersPF'},$hash{'rawReads'},$hash{'trimmedReads'},$hash{'totalReads'},$hash{'totalSeq'},$hash{'targetReads'},$hash{'phixReads'},$hash{'primerDimerReads'},$hash{'other'},$hash{'OTA_SUM'},$hash{'targetWtReads'}"."$hash{'mutLine'}\n";
for (my $i=0; $i<scalar(@mutantLines); $i++) {
	print OUT "$hash{'runId'},$hash{'runFolder'},$hash{'sampleNumber'},$hash{'sampleName'},$hash{'assay'},$hash{'input'},$hash{'source'},$hash{'expectedCN'},$hash{'type'},$hash{'tool'},$hash{'environment'},$hash{'samplePlate'},$hash{'sampleWell'},$hash{'i7IndexID'},$hash{'index'},$hash{'standardGroup'},$hash{'batch'},$hash{'checkoutNumber'},$hash{'ngPerRxn'},$hash{'phixFraction'},$hash{'projectVersion'},$hash{'clustersRaw'},$hash{'clustersPF'},$hash{'rawReads'},$hash{'trimmedReads'},$hash{'totalReads'},$hash{'totalSeq'},$hash{'targetReads'},$hash{'phixReads'},$hash{'primerDimerReads'},$hash{'other'},$hash{'OTA_SUM'},$hash{'targetWtReads'}".",$mutantLines[$i]\n";
}

close OUT;

print "\n";
print "Sample specific CSV file generated: $outfile\n";
print "\n";

# take IGV snapshot of target region
if ($inputs{mode} == 1) {
	try {
		takeIGVSnapshot($targetChr,$targetStart,$targetEnd,$finalBAM);
	} catch {
		print "WARNING: Encountered error taking IGV snapshot: $_\n";
	};
}

# run BAMSTATS on sorted.bam IFF option enabled
if ($inputs{outputBAMSTATS}) {
	# java -jar -Xmx4g BAMStats-1.25.jar -i <BAM file>
	$CMD = "java -jar -Xmx8g $paths{BAMSTATS} -d -l -m -q -s -i $finalBAM -o $finalBAM"."_bamstats.txt";
	print "Running command: $CMD\n";
	#IF SGE
	if ($inputs{sge}) {
		my $jname = $name;
		#$jname =~ s/^[0-9]+//ig;
		#$jname =~ s/^-+//ig;
		#$jname =~ s/^_+//ig;
		$sge->set("jobname",($jname."_BAMSTATS"));
		$sge->set("seed",$sampleNumber);
		$sge->set("numcpus",4);
		$CMD = "/usr/bin/time -v " . $CMD;
		$sge->pleaseExecute_andWait("$CMD");
		sleep(5);
	}
	else {
		system($CMD);
	}
	print "\n";
}

## DONE ##

print "\n\n\n";
print "Start time: "; print join ' ', $dtStart->ymd, $dtStart->hms; print "\n";
my $dtEnd = DateTime->now;
print "End time: "; print join ' ', $dtEnd->ymd, $dtEnd->hms; print "\n";
my $span = DateTime::Format::Human::Duration->new();
print 'Total elapsed time: ', $span->format_duration_between($dtEnd, $dtStart); print "\n\n";
print "===PROCESSING $name COMPLETE===\n";
exit 0;










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
	return \@list;
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
		#if ($doOut == 1) {
			push @sampleSheet, $line;
			#print "$line\n";
		#}
		#elsif ($line =~ /^Sample_ID/i) {
		#	$doOut = 1;
		#}
	}
	close SS;
	#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,GenomeFolder,Sample_Project,Description,Input,Source
	#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description,Input,Source,Batch
	
	# figure out what line the header is on
	my $headerIdx = 0;
	for (my $i=0; $i<scalar(@sampleSheet); $i++) {
		my $line = $sampleSheet[$i];
		chomp($line);
		if ($line =~ m/^Sample_ID/) {
			$headerIdx = $i;
		}
	}
	#$headerIdx = $headerIdx + 1;
	#print "HEADER LINE IDX: $headerIdx\n"; sleep(120);
	
	# figure out what index the Sample_project field is
	my $idx = 0;
	my $inputIdx = 0;
	my $sourceIdx = 0;
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
		elsif ($s[$i] =~ m/input/i) {
			$inputIdx = $i;
		}
		elsif ($s[$i] =~ m/source/i) {
			$sourceIdx = $i;
		}
	}
	
	for (my $i = ($headerIdx+1); $i<scalar(@sampleSheet); $i++) {
		next if ($sampleSheet[$i] =~ m/^#/i);
		my @s = split(",",$sampleSheet[$i]);
		#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,GenomeFolder,Sample_Project,Description,Input,Source
		#Sample_ID,Sample_Name,Sample_Plate,Sample_Well,I7_Index_ID,index,Sample_Project,Description,Input,Source,Batch
		my $assay = "NA";
		if ($s[$idx] =~ /(kras|G12)/i) {
			$assay = "KRAS_G12X"; }
		elsif ($s[$idx] =~ /ex19|exon19|del/i) {
			$assay = "EGFR_EX19DEL"; }
		elsif ($s[$idx] =~ /l858/i) {
			$assay = "EGFR_L858R"; }
		elsif ($s[$idx] =~ /t790/i) {
			$assay = "EGFR_T790M"; }
		elsif ($s[$idx] =~ /braf/i) {
			$assay = "BRAF_V600X"; }
		else { warn "WARNING: Could not find assay for sample line $i in $sampleSheetFile\n"; next; }
		$sampleAssayHash{$s[0]}{'assay'} = $assay;
		
		if ($inputIdx != 0) {
			$sampleAssayHash{$s[0]}{'input'} = int($s[$inputIdx]);
		}
		else {
			$sampleAssayHash{$s[0]}{'input'} = " ";
		}
		
		if ($sourceIdx != 0) {
			$sampleAssayHash{$s[0]}{'source'} = int($s[$inputIdx]);
		}
		else {
			$sampleAssayHash{$s[0]}{'source'} = " ";
		}
	}
	
	return \%sampleAssayHash;
	
	#print "FOUND ASSAY: $assay\n"; sleep(120);
}

sub getTargetFromAssay {
	my $assay = shift;
	my $target = "NA";
	my $wtSeq = "NA";
	foreach my $line (@targets) {
		next if ($line =~ /^#/);
		#chr	start	stop	name	wtSeq
		my @s = split("\t",$line);
		if ($s[3] =~ m/$assay/i) {
			$target = "$s[0]:$s[1]-$s[2]";
			chomp($s[4]);
			$wtSeq = $s[4];
			last;
		}
	}
	return ($target, $wtSeq);
}

sub getMutantsCoordsFile {
	my $assay = shift;
	my $file = "NA";
	my $base = catfile($baseDir,"data");
	if ($assay =~ /kras_g/i) {
		#$file = "/home/palak/isilon/KRAS_G12X_mutants_coords.bed"; 
		$file = catfile($base,"KRAS_G12X_mutants_coords.bed"); }
	elsif ($assay =~ /ex19|exon19|del/i) {
		#$file = "/home/palak/isilon/EGFR_EX19DEL_mutants_coords.bed"; 
		$file = catfile($base,"EGFR_EX19DEL_mutants_coords.bed"); }
	elsif ($assay =~ /l858/i) {
		#$file = "/home/palak/isilon/EGFR_L858R_mutants_coords.bed";
		$file = catfile($base,"EGFR_L858R_mutants_coords.bed"); }
	elsif ($assay =~ /t790/i) {
		#$file = "/home/palak/isilon/EGFR_T790M_mutants_coords.bed"; 
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
	# ensure that each start coordinate is unique for SNP assays
	if ($file !~ /ex19del/i) {
		my %outHash;
		foreach my $line (@mutantsCoords) {
			chomp($line);
			my @s = split("\t",$line);
			chomp(@s);
			# unique based on start coordinate
			$outHash{$s[1]} = $line;
		}
		@mutantsCoords = ();
		foreach my $key (sort keys %outHash) {
			push @mutantsCoords, $outHash{$key};
		}
	}
	return \@mutantsCoords;
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
		#$file = "/home/palak/isilon/BRAF_V600X_mutants_coords.bed"; 
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

sub takeIGVSnapshot {
	my $chr = shift;
	my $start = shift;
	my $stop = shift;
	my $bam = shift;
	
	# IGV server
	my $server = $inputs{'IGVSERVER'};
	
	# check if IGV is connectable
	my $retryMax = 10;
	my $retryCount = 0;
	my $connectable = 0;
	while ($retryCount <= $retryMax && $connectable == 0) {
		my $CMD = "nc -zv $server 60151 2>&1";
		my $return = qx($CMD);
		if ($return =~ m/refused/i) {
			print "IGV is not connectable on remote server $server. Waiting to try again...\n";
			print "\tRESPONSE: $return\n";
			sleep(15);
			$retryCount++;
		}
		elsif ($return =~ m/succeeded/i) {
			print "IGV is connectable on remote server $server!\n";
			$connectable = 1;
			last;
		}
	}
	
	# IF IGV is not connectable, start it locally
	if ($connectable == 0) {
		print "IGV is not connectable on remote server $server. Starting it locally...\n";
		$server = "127.0.0.1";
		# check if IGV is running if not start it
		my $CMD = "ps -eo args | grep [i]gv.jar | wc -l";
		print "Checking if IGV is running...\n";
		my $return = qx($CMD);
		print "\tRESPONSE: $return\n";
		chomp($return);
		if (int($return) < 2) {
			$CMD = "/bin/bash $paths{IGV} &";
			print "IGV not running. Starting it now...\n";
			print "Running command: $CMD\n";
			system($CMD);
			sleep(120); # wait for IGV to start
		}
		else {
			print "IGV is running locally. Checking if connectable...\n";
			# check if connectable, if not wait some time and try again up to 5-6 times
			my $retryMax = 12;
			my $retryCount = 0;
			while ($retryCount <= $retryMax && $connectable == 0) {
				my $CMD = "nc -zv $server 60151 2>&1";
				my $return = qx($CMD);
				if ($return =~ m/refused/i) {
					print "IGV is not connectable locally at $server. Waiting to try again...\n";
					print "\tRESPONSE: $return\n";
					sleep(10);
					$retryCount++;
				}
				elsif ($return =~ m/succeeded/i) {
					print "IGV is connectable locally at $server!\n";
					$connectable = 1;
					last;
				}
			}
		}
	}
	
	# IGV should be up and running and connectable here either on remote server or locally
	if ($connectable == 1) {
		print "Taking IGV snapshot...\n";
		# only run if IGV is connectable
		my $CMD = "nc -zv $server 60151 2>&1";
		my $return = qx($CMD);
		#print "\tRESPONSE: $return\n";
		if ($return =~ m/succeeded/i) {
			try {
				# do interaction and get snapshot
				if ($start == $stop) {
					$start = $start - 1;
					$stop = $stop + 1;
				}
				my $locus = "$chr:$start-$stop";
				print "IGV is connectable at $server. Taking snapshot of $locus\n";
				require($paths{IGVLIB});
			
				my $socket = igv_connect($server);
			
				igv_new($socket);
				my @files;
				push @files, $bam;
				igv_load($socket,@files);
				igv_genome($socket,"hg19");
			
				igv_maxPanelHeight($socket, 5000000);
				igv_snapshotDirectory($socket, "$inputs{outdir}");
			
				my $regionStart = $start + 50;
				my $regionStop = $stop - 50;
				my $locus2 = "$chr:$regionStart-$regionStop";
				my $file = "$name"."_"."$assay"."_".$chr."_".$start."_"."$stop"."_top2500.jpg";
				#my $file2 = "$name"."_"."$assay"."_".$chr."_".$start."_"."$stop.svg";

				igv_goto($socket, $locus2);
				igv_region($socket, $chr, $regionStart, $regionStop);
				#igv_preference($socket,"IGV.track.height","10");
				#igv_preference($socket,"IGV.chart.track.height","20");
				#igv_preference($socket,"SAM.DOWNSAMPLE_READS","true");
				igv_preference($socket,"SAM.MAX_LEVELS","2500");
				#igv_collapse($socket);
				igv_sort($socket, "MUTATION_COUNT", $locus);
				igv_snapshot($socket, $file);
				#igv_snapshot($socket, $file2);
				
				#igv_close($socket);
				
				print "IGV snapshot saved as: $file\n";
			} catch {
				print "WARNING: Encountered error taking IGV snapshot: $_\n";
			};
		}
	}
	else {
		print "WARNING: Could not communicate with IGV server at $inputs{IGVSERVER}. Could not start IGV locally. Skipping IGV Snapshot...\n\n";
	}
	print "\n";
}

sub verifyFastqGzIntegrity {
	my $fqIn = shift;
	my $CMD = "gunzip -t $fqIn 2>&1";
	print "Running command: $CMD\n";
	my $output = qx($CMD);
	if (length($output) != 0) {
		die "ERROR: Corrupted FASTQ file: $fqIn! Exiting...\n";
	}
}

sub verifyFastqGzIntegrity_returnCode {
	my $fqIn = shift;
	my $CMD = "gunzip -t $fqIn 2>&1";
	print "Running command: $CMD\n";
	my $output = qx($CMD);
	if (length($output) != 0) {
		return 0;
	}
	else {
		return 1;
	}
}

sub countSanityCheck {
	my $ref = shift;
	my %hash = %$ref;
	# totalReads = totalSeq + primer + Other
	if ( $hash{'totalReads'} != ($hash{'totalSeq'} + $hash{'primerDimerReads'} + $hash{'other'}) ) {
		die "ERROR: TrimmedFilteredReads DOES NOT EQUAL (TotalMappedReads + PrimerArtifacts + Other)\n";
	}
	# totalSeq = totalTarget + PhiX + OTA
	if ( $hash{'totalSeq'} != ($hash{'targetReads'} + $hash{'phixReads'} + $hash{'OTA_SUM'}) ) {
		die "ERROR: TotalMappedReads DOES NOT EQUAL (TotalTargetReads + PhiXReads + OTA)\n";
	}
	print "\nReadsProcessing counts sanity check completed successfully!\n\n";
}


sub Usage {
	print "Usage: perl generate_RAWCOUNTS_singleFastq.pl --fastq /Data/Intensities/BaseCalls/input.fastq --outdir /path/to/outfolder --tempdir /path/to/outfolder/temp --cpus cpus/jobs --Qmin minQscore N --MAPQmin N --mismatch 0.N --percentBases N --bwaMaxGaps N --bwaMaxGapExts N --bwaGapOpenPen N --bwaGapExtPen N --bwaMismatchPen N --ref reference fasta --assay sample assay --input input volume 10/60 --source sample source P/U --mtCoordsFile mutant coordinates file --adaptersFile adapter seqs to trim --primersFile seqs to flag primer-dimers --targetsFile assay targets file [--sge flag to use SGE scheduler] [--sgeQ SGE queue to submit to] [--sgePE SGE parallel environment name] --runId runId of run [[--mode 1/2]]  [--keepTemp] [--noTrimming] [--Nmask] [--minlen minimum read length after trimming] [--overlap minimum number of bases to trim] [--clustersRaw] [--clustersPF] [--type] [--tool] [--samplePlate] [--sampleWell] [--i7IndexID] [--index] [--standardGroup] [--batch] [--checkoutNumber] [--ngPerRxn] [--phixFraction] [--projectVersion] --CUTADAPT --FASTQ_QUAL_FILTER --BWA --SAMTOOLS --BAMREADCOUNT --FASTQC --IGVLIB --IGV --BAMSTATS --outputBAMSTATS --MAXSLEEPDELAY\n";
}
