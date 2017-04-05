# save output, comprised of the summary, stats, and plots files
save_output <- function(output_dir,runid,summary_dfrm,stats_dfrm,all_exp_plot_list) {
	
	####################
	# save summary.csv #
	####################

	summary_filepath <- file.path(output_dir,paste(runid,'_summary.csv',sep=''))
	write.csv(summary_dfrm,file=summary_filepath,row.names=F,na='')
	
	####################
	# save summary.csv #
	####################

	stats_filepath <- file.path(output_dir,paste(runid,'_stats.csv',sep=''))
	write.csv(stats_dfrm,file=stats_filepath,row.names=F,na='')

	#########################
	# save plots as one pdf #
	#########################

	if (length(unlist(all_exp_plot_list)) > 0) {
		plot_filepath <- file.path(output_dir,paste(runid,'_all_plots.pdf',sep=''))
		pdf(file=plot_filepath, onefile = TRUE)
		invisible(lapply(all_exp_plot_list, function(exp_plot_list) { invisible(lapply(exp_plot_list, print)) }))
		dev.off()
	}

	return(NA)
}
