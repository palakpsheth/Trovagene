#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(base))
thisFile <- function() {
        cmdArgs <- commandArgs(trailingOnly = FALSE)
        needle <- "--file="
        match <- grep(needle, cmdArgs)
        if (length(match) > 0) {
                # Rscript
                return(normalizePath(sub(needle, "", cmdArgs[match])))
        } else {
                # 'source'd via R console
                return(normalizePath(sys.frames()[[1]]$ofile))
        }
}
script.dir <- dirname(thisFile())
.libPaths(c(script.dir,.libPaths()))
suppressPackageStartupMessages(library(getopt))

#suppressPackageStartupMessages(library(getopt))
#suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(MASS))
suppressPackageStartupMessages(library(dplyr))
#suppressPackageStartupMessages(library(gridExtra))
#suppressPackageStartupMessages(library(ini))

spec = matrix(c('runid','r',1,"character","Run ID",
                'config_filepath','c',1,"character","Configuration .ini file",
                'da_dir','d',1,"character","Data analysis directory",
                'rawcounts_filepath','i',1,"character","Raw read counts .csv file",
                'stats_filepath','s',1,"character","Overall run stats .csv file",
                'output_dir','o',1,"character","Output directory for summary.csv and plots"), ncol = 5, byrow = TRUE)

options = getopt(spec)

.libPaths(c(options$da_dir,.libPaths()))
suppressPackageStartupMessages(library(ini))
suppressPackageStartupMessages(library(gridExtra))
suppressPackageStartupMessages(library(ggplot2))

# print flag definitions for quick reference
flags <- list(	'NS'=c('Negative or zero slope in regression'),
				'LB'=c('Lambda on boundary of parameter space'),
				'HS'=c('Hot sample'),
                                'SQ'=c('Sample (non-NTC) failed reads QC'),
                                'NQ'=c('NTC failed reads QC'),
                                'GQ'=c('Standard group failed QC') )
cat(sprintf('\nAbbreviation reference for FLAGS:\n\n'))
cat(sprintf('\t%s: %s\n',names(flags),unlist(flags)),sep='')
cat('\n')

# source ancillary functions in da_dir
source(file.path(options$da_dir,'analyze_data.r'))
source(file.path(options$da_dir,'append_stats_dfrm.r'))
source(file.path(options$da_dir,'find_max_cor_lambda.r'))
source(file.path(options$da_dir,'get_FitCN_pred_int.r'))
source(file.path(options$da_dir,'get_FitCN.r'))
source(file.path(options$da_dir,'get_GEq.r'))
source(file.path(options$da_dir,'get_pred_band.r'))
source(file.path(options$da_dir,'get_x_inv_trans.r'))
source(file.path(options$da_dir,'get_x_trans.r'))
source(file.path(options$da_dir,'get_y_inv_trans.r'))
source(file.path(options$da_dir,'get_y_trans.r'))
source(file.path(options$da_dir,'parse_config_file.r'))
source(file.path(options$da_dir,'process_exp.r'))
source(file.path(options$da_dir,'save_output.r'))
source(file.path(options$da_dir,'withJavaLogging.r'))

setwd(options$da_dir)

# call main function
withJavaLogging({
	data_analysis <- analyze_data(options$runid,options$config_filepath,options$rawcounts_filepath,options$stats_filepath,options$output_dir)
})
