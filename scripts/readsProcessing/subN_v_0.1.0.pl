#!/usr/bin/perl -w

#PROGRAM: 
#subN = SUBstitute as N for the bases whose quality score is less than the quality cutoff 
#USAGE EXAMPLE:>perl subN_v_0.1.0.pl -i my_input.fastq.gz -o my_output.fastq.gz

#!/usr/bin/perl -w

use strict;
use Getopt::Long;
use Pod::Usage;
#use IO::File;
use File::Basename;
#use IO::Uncompress::Gunzip qw(gunzip $GunzipError) ;
#use IO::File ;
#use PerlIO::gzip;
use List::MoreUtils qw(uniq);

###################################################################################
#GETTING OPTIONS OR DISPLAY HELP MESSAGE
###################################################################################

#my $qcutoff = 53; #CUTOFF QUALITY SCORE IN SANGER ASCII FASTQ (DEFAULT: ASCII 53 == Qscore 20). THE BASE WHOSE QUALITY IS BELOW THE CUTOFF WILL BE WILL BE SUBSTITUTED AS N. 
my $qcutoff = 20; #CUTOFF QUALITY SCORE IN QSCORE FORMAT [CONVERTED INTO ASCII FORMAT] (DEFAULT: Qscore 20 == ASCII 53). THE BASE WHOSE QUALITY IS BELOW THE CUTOFF WILL BE WILL BE SUBSTITUTED AS N. 
my $help = 0;
my $man = 0;
my $input_file;
my $output_file;

GetOptions ('h|help' => \$help, 
			'm|man' => \$man,
			'q|qcutoff=f' => \$qcutoff,
	        'i|in=s' => \$input_file,
            'o|out=s' => \$output_file) or pod2usage(1);
pod2usage( -verbose => 1 ) if ($help);
pod2usage( -exitstatus => 0, -verbose => 2 ) if ($man);

# CHECK FOR REQUESTED INPUT FILE
if (!defined($input_file))
{
	pod2usage( -exitstatus => 2);
}

if (!defined($output_file))
{
	pod2usage( -exitstatus => 2);
	#$output_file = Getting_Output_File_Name($input_file);
}

# CONVERT QSCORE TO ASCII
print "Using Qscore cutoff: $qcutoff\n";
#$qcutoff = chr($qcutoff);

###################################################################################
#READ THE INPUT FILE BY FOUR LINES
###################################################################################

#my $input = new IO::File "<$input_file" or die "ERROR: Cannot open $input_file: $!\n" ;
#my $buffer;
#gunzip $input => \$buffer or die "ERROR: gunzip failed: $GunzipError\n";

open (my $gzip_fh, "| /bin/gzip -c > $output_file") or die "ERROR: error starting gzip $!\n";

#open IN, "<:gzip", "$input_file" or die "ERROR: Cannot open $input_file: $!\n" ;

open(IN, sprintf("zcat %s |", $input_file)) or die("ERROR: Can't open pipe from command zcat $input_file : $!\n");

my $ncount = 0;
my @reads = 0;
my @total = 0;
while (<IN>)
{
	chomp(my $line1 = $_);
	chomp(my $line2 = <IN>);
	chomp(my $line3 = <IN>);
	chomp(my $line4 = <IN>);

	$line1 =~ s/\s+//;
	$line2 =~ s/\s+//;
	$line3 =~ s/\s+//;
	$line4 =~ s/\s+//;

	my $sequence = $line2;
	my $qvalue = $line4;
	push @total, $line1;

	my @sequence_array = split('', $sequence); #CONVERT SEQUENCE TO AN ARRAY
	my @qvalue_array = unpack("C*", $qvalue); #CONVERT QVALUE TO AN ARRAY WITH ASCII VALUE
	#my @qvalue_array = split('', $qvalue); #CONVERT QVALUE TO AN ARRAY 

	my $i = 0;
	foreach my $each_qvalue (@qvalue_array)
	{
		$each_qvalue = $each_qvalue - 33; # ILLUMINA IS ASCII-33 encoding
		if ($each_qvalue < $qcutoff)
		{
			$sequence_array[$i] = 'N';
			$ncount++;
			push @reads, $line1;
			#print "Qscore: $each_qvalue\n";
		}
		$i++;
	}
	my $new_sequence = join('', @sequence_array);

	print $gzip_fh "$line1", "\n";
	print $gzip_fh "$new_sequence", "\n"; 
	print $gzip_fh "$line3", "\n";
	print $gzip_fh "$qvalue", "\n";
}

close $gzip_fh;
close IN;

@reads = uniq(@reads);
@total = uniq(@total);
my $percent = (scalar(@reads)/scalar(@total)) * 100;
$percent = sprintf("%.2f", $percent);
print "Total new N bases: $ncount in ".scalar(@reads)."/".scalar(@total)." reads ($percent"."%)\n";

























###################################################################################
###################################################################################
#FUNCTIONS
###################################################################################
###################################################################################



sub Getting_Output_File_Name {
    my $input_file = shift;
    my $basename = basename($input_file,".fastq.gz");
    my $output_file = $basename."_minQ$qcutoff"."masked.fastq.gz";
    return $output_file;
}

