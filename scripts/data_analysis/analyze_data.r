# analyze data from rawcounts csv with configuration options specified by config_filepath, stats file specified by stats_filepath
analyze_data <- function(runid,config_filepath,rawcounts_filepath,stats_filepath,output_dir) {
	# parse configuration file
	#config_options <- parse_config_file(config_filepath)
	config_options <- read.ini(config_filepath)

	# load raw counts file from reads preprocessing module
	rawcounts_dfrm <- read.csv(rawcounts_filepath, header=T, stringsAsFactors=F)
	stats_dfrm <- read.csv(stats_filepath, header=T, stringsAsFactors=F)

	#runid <- unique(rawcounts_dfrm$RunId)		# NOTE: should only be one runid per run -- just take runid as parameter as safeguard

	# parse raw counts file for unique assay/source/stdgroup combos
	exp_list <- unique(rawcounts_dfrm[,c('Assay','Source','Input','StandardGroup')])
	cat(sprintf('Unique experiments:\n'))
	print(exp_list, row.names=FALSE)

	# list of plots to be included in one pdf
	all_exp_plot_list <- list()
	summary_dfrm <- NULL

	for (exp_row in 1:nrow(exp_list)) {
		exp <- exp_list[exp_row,]
		exp_output <- process_exp(exp,runid,config_filepath,config_options,rawcounts_dfrm,stats_dfrm)
		summary_dfrm <- rbind(summary_dfrm,exp_output$exp_dfrm)		# adding columns so must rbind
		stats_dfrm <- exp_output$stats_dfrm								# adding rows so replace
		if (length(exp_output$exp_plot_list) > 0) {
			i <- length(all_exp_plot_list)+1		# not guaranteed to have standards for each experiment, so increment appropriately
			all_exp_plot_list[[i]] <- exp_output$exp_plot_list				# adding elements to list
		}
	}

	# save output
	save_output(output_dir,runid,summary_dfrm,stats_dfrm,all_exp_plot_list)

	cat(sprintf('Finished analyzing data on runid %s\n',runid))

	return(list(summary_dfrm=summary_dfrm,stats_dfrm=stats_dfrm,all_exp_plot_list=all_exp_plot_list))
}
