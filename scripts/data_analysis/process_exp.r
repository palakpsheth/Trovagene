# processes an individual experiment, defined as a unique assay/input/source/standard group combination
process_exp <- function(exp,runid,config_filepath,config_options,rawcounts_dfrm,stats_dfrm) {
	assay <- exp$Assay
	input <- exp$Input
	source <- exp$Source
	std_group <- exp$StandardGroup

	cat(sprintf('\n########################################################################\n'))
	cat(sprintf('Processing assay %s, input %s, source %s, with standard group %d\n',assay,input,source,std_group))
	cat(sprintf('########################################################################\n'))
	
	exp_dfrm <- rawcounts_dfrm[rawcounts_dfrm$Assay == assay & rawcounts_dfrm$Input == input & rawcounts_dfrm$Source == source & rawcounts_dfrm$StandardGroup == std_group,]

	tp.dir <- system("pwd", intern = TRUE) #should be <DEV>/scripts/data_analysis
	tp.dir <- dirname(tp.dir) # returns to <DEV>/scripts/
	tp.dir <- dirname(tp.dir) # returns to <DEV>

	bed_dfrm <- read.table(file.path(tp.dir,config_options[[paste(assay,source,sep='_')]]$mtCoordsFile),sep='\t',header=T,stringsAsFactors=F,comment.char='')
	# NOTE: are there other lines that have leading '#'?  currently not (20161016), but if so, need to remove these lines
	names(bed_dfrm) <- gsub('X.','',names(bed_dfrm))		# header row has leading '#' which is converted to 'X.'

	# get STD group QC data
	load(file.path(tp.dir,config_options$dataAnalysis$std_group_qc_file))

	cat(sprintf('Determining mutants and associated counts\n'))
	exp_dfrm <- cbind(exp_dfrm, do.call('rbind', lapply(1:nrow(exp_dfrm), function(i) {
		snum <- exp_dfrm$SampleNumber[i]
		chr <- exp_dfrm$Chr[i]
		start <- exp_dfrm$Start[i]
		seq <- exp_dfrm$Sequence[i]
		count <- exp_dfrm$Count[i]

		# uniquely identified by chr/start/seq
		mut_bed_dfrm <- bed_dfrm[bed_dfrm$chr == chr & bed_dfrm$start == start & bed_dfrm$seq == seq,]

		if (nrow(mut_bed_dfrm) > 0) {
			# NOTE: WT exists for all assays except for Ex19del
			mut_type <- mut_bed_dfrm$type[mut_bed_dfrm$chr == chr & mut_bed_dfrm$start == start & mut_bed_dfrm$seq == seq]
			MutationName <- ifelse(mut_type %in% c('prim_MT','alt_MT'),mut_bed_dfrm$name,
								ifelse(mut_type == 'WT','WT',NA))
			# in all bed files, 'name' is either mutation name or 'WT' (only one WT for unique chr/start) -- this means for WT, name == 'WT' and type == 'WT' in bed file

			# only populate MTcount if known mutant
			MTcount <- ifelse(!is.na(MutationName) & MutationName != 'WT',count,NA)
		} else {
			MutationName <- NA
			MTcount <- NA
		}

		return(data.frame(MutationName=MutationName,MTcount=MTcount))
	})))
	cat(sprintf('Finished mutant classification\n'))

	########################################################
	# load configuration options for this assay/source/mut #
	########################################################

	# hot sample scalar (currently defined to be 30 percent above highest STD CN level -- not assay/source specific)
	hs_scalar <- as.numeric(config_options$dataAnalysis$hs_scalar)
	ntc_maxreads <- as.numeric(config_options$dataAnalysis$ntc_maxreads)
	# reads QC params
	if (is.null(config_options[[paste(assay,source,sep='_')]]$reads_qc_col) | is.null(config_options[[paste(assay,source,sep='_')]]$minreads)) {
		cat(sprintf('WARNING: No reads QC parameters specified for assay %s input %g source %s.  Bypassing reads QC.  Please see data analysis log file for additional details...\n',assay,input,source))
		perform_reads_qc <- F
	} else {
		reads_qc_col <- as.character(config_options[[paste(assay,source,sep='_')]]$reads_qc_col)
		minreads <- as.numeric(config_options[[paste(assay,source,sep='_')]]$minreads)
		cat(sprintf('Minimum reads threshold on %s: %d\n',reads_qc_col,minreads))
		perform_reads_qc <- T
	}
	# STD group QC param
	if (is.null(config_options[[paste(assay,source,sep='_')]]$std_group_qc_alpha)) {
		cat(sprintf('WARNING: No STD group QC parameter specified for assay %s input %g source %s.  Bypassing reads QC.  Please see data analysis log file for additional details...\n',assay,input,source))
		perform_std_group_qc <- F
	} else {
		std_group_qc_alpha <- config_options[[paste(assay,source,sep='_')]]$std_group_qc_alpha
		perform_std_group_qc <- T
	}

	########################
	# initialize variables #
	########################

	exp_dfrm$FLAGS <- NA 		# possible indicators of problems
	exp_dfrm$QC <- 'PASS'
	exp_dfrm$bias_adj <- NA
	exp_dfrm$adj_mutant_reads <- NA
	exp_dfrm$DetectionThreshold <- NA
	exp_dfrm$DetectCall <- NA
	exp_dfrm$FitCN <- NA
	exp_dfrm$FitCN_lower <- NA
	exp_dfrm$FitCN_upper <- NA
	exp_dfrm$LLoQ <- NA
	exp_dfrm$GEq <- NA
	exp_dfrm$GEq_lower <- NA
	exp_dfrm$GEq_upper <- NA
	exp_plot_list <- list()

	#############################################
	# initialize exp specific counters/switches #
	#############################################

	sg_qc_fail <- F

	########
	# LLoQ #
	########

	if (is.null(config_options[[paste(assay,source,sep='_')]]$LLoQ)) {
		cat(sprintf('WARNING: No LLoQ specified for assay %s input %g source %s.  Please see data analysis log file for additional details...\n',assay,input,source))
	} else {
		exp_dfrm$LLoQ <- as.numeric(config_options[[paste(assay,source,sep='_')]]$LLoQ)
	}

	####################
	# non-NTC reads QC #
	####################

	if (perform_reads_qc) {
		cat(sprintf('Performing sample reads QC on all non-NTC samples...\n'))
		fail_reads_qc_ind <- which(exp_dfrm[[reads_qc_col]] < minreads & !grepl('NTC|CTLn|CTXn|CTn',exp_dfrm$Name,ignore.case=T))
		if (length(fail_reads_qc_ind) > 0) {
			exp_dfrm$QC[fail_reads_qc_ind] <- 'FAIL'
			exp_dfrm$FLAGS[fail_reads_qc_ind] <- ifelse(is.na(exp_dfrm$FLAGS[fail_reads_qc_ind]),'SQ',paste(exp_dfrm$FLAGS[fail_reads_qc_ind],';SQ',sep=''))
			cat(sprintf('WARNING: One or more samples failed reads QC for assay %s input %g source %s. Please see data analysis log file for additional details...\n',assay,input,source))
			cat(sprintf('The following samples failed reads QC:\n'))
			print(unique(exp_dfrm[fail_reads_qc_ind,c('Name','SampleNumber')]), row.names=FALSE)
		}
		cat(sprintf('Finished sample reads QC\n\n'))
	}

	################
	# NTC reads QC #
	################

	# always performed for any assay
	cat(sprintf('Performing sample reads QC on all NTC samples...\n'))
	ntc_fail_reads_qc_ind <- which(exp_dfrm$TrimmedFilteredReads > ntc_maxreads & grepl('NTC|CTLn|CTXn|CTn',exp_dfrm$Name,ignore.case=T))
	if (length(ntc_fail_reads_qc_ind) > 0) {
		exp_dfrm$QC[ntc_fail_reads_qc_ind] <- 'FAIL'
		exp_dfrm$FLAGS[ntc_fail_reads_qc_ind] <- ifelse(is.na(exp_dfrm$FLAGS[ntc_fail_reads_qc_ind]),'NQ',paste(exp_dfrm$FLAGS[ntc_fail_reads_qc_ind],';NQ',sep=''))
		cat(sprintf('WARNING: One or more NTCs failed reads QC for assay %s input %g source %s. Please see data analysis log file for additional details...\n',assay,input,source))
		cat(sprintf('The following samples failed reads QC:\n'))
		print(unique(exp_dfrm[ntc_fail_reads_qc_ind,c('Name','SampleNumber')]), row.names=FALSE)
	}


	#########################
	# prediction generation #
	#########################
	
	prim_muts <- unique(bed_dfrm$name[bed_dfrm$type == 'prim_MT'])
	alt_muts <- unique(bed_dfrm$name[bed_dfrm$type == 'alt_MT'])
	for (mut in prim_muts) {
		cat(sprintf('Analyzing mutant %s...\n',mut))

		########################################################
		# load configuration options for this assay/source/mut #
		########################################################

		if (is.null(config_options[[paste(assay,source,sep='_')]][[paste('threshold',mut,sep='_')]]) | is.null(config_options[[paste(assay,source,sep='_')]][[paste('dist_factor',mut,sep='_')]]) | is.null(config_options[[paste(assay,source,sep='_')]]$lowest_nonzero_std_level)) {
			cat(sprintf('WARNING: Missing detection parameters for mutant %s assay %s input %g source %s.  Please see data analysis log file for additional details...\n',mut,assay,input,source))
			perform_detection <- F
		} else {
			detection_threshold <- as.numeric(config_options[[paste(assay,source,sep='_')]][[paste('threshold',mut,sep='_')]])
			dist_factor <- as.numeric(config_options[[paste(assay,source,sep='_')]][[paste('dist_factor',mut,sep='_')]])
			lowest_nonzero_std_level <- as.integer(config_options[[paste(assay,source,sep='_')]]$lowest_nonzero_std_level)
			cat(sprintf('Threshold: %f\n',detection_threshold))
			cat(sprintf('Distance factor: %f\n',dist_factor))
			cat(sprintf('Lowest nonzero STD level: %d\n',lowest_nonzero_std_level))
			perform_detection <- T
		}

		mut_dfrm <- exp_dfrm[which(exp_dfrm$MutationName == mut),]												# primary mutation samples within this exp
		std_mut_dfrm <- mut_dfrm[which(mut_dfrm$Type == 'Standard'),]											# primary mutation samples that are STDs (for regression)
		std_ctl_mut_dfrm <- mut_dfrm[which(grepl('Standard',mut_dfrm$Type,ignore.case=T) | grepl('Control',mut_dfrm$Type,ignore.case=T)),]											# primary mutation samples that are standards, historic standards, or controls, to check that ExpectedCN is provided
		mut_alt_dfrm <- exp_dfrm[which(exp_dfrm$MutationName == mut | exp_dfrm$MutationName %in% alt_muts),]	# primary mutation and alternate mutation samples that are fit using primary mutation regression

		if (nrow(std_mut_dfrm) == 0) {
			# this can be expected -- likely an R&D experiment interested in just reads
			# do nothing -- fields already preallocated to be NA (FitCN, FitCN_lower, FitCN_upper, DetectCall)
			cat(sprintf('WARNING: No standards found for mutant %s assay %s input %g source %s\n',mut,assay,input,source))
		} else {
			cat(sprintf('Standards found for mutant %s\n',mut))

			# include warning if standards/controls have do not have an ExpectedCN (should be populated by SSV)
			if (any(is.na(std_ctl_mut_dfrm$ExpectedCN))) {
				cat(sprintf('\nWARNING: One or more standards/controls do not have an expected CN value for mutant %s assay %s input %g source %s. Please see data analysis log file for additional details...\n',mut,assay,input,source))
				print(unique(std_ctl_mut_dfrm[is.na(std_ctl_mut_dfrm$ExpectedCN),c('Name','SampleNumber','QC','ExpectedCN','Type')]), row.names=FALSE)
				cat(sprintf('\n'))
			}

			# check that there are a sufficient number of standards at each CN level that pass QC (at least 2 STDs passing QC at each CN level)
			cn_levels <- unique(std_mut_dfrm$ExpectedCN[which(!is.na(std_mut_dfrm$ExpectedCN))])
			suff_num_stds_pass_qc <- unlist(lapply(cn_levels, function(cn_level) { nrow(std_mut_dfrm[which(std_mut_dfrm$ExpectedCN == cn_level & std_mut_dfrm$QC == 'PASS'),]) >= 2 }))

			# get the max STD CN level
			max_std_expCN <- max(std_mut_dfrm$ExpectedCN,na.rm=T)

			# primary and alt mutation indices
			mut_alt_ind <- which(exp_dfrm$MutationName == mut | exp_dfrm$MutationName %in% alt_muts)

			if (!sum(suff_num_stds_pass_qc) >= 4) {
				cat(sprintf('WARNING: Not a sufficient number of standards passing QC (need at least 2 standards passing QC for at least 4 CN levels) for mutant %s assay %s input %g source %s. Cannot generate predictions for this standard group. Please see data analysis log file for additional details...\n',mut,assay,input,source))
				cat(sprintf('All standards which have ExpectedCN:\n'))
				print(unique(std_mut_dfrm[!is.na(std_mut_dfrm$ExpectedCN),c('Name','SampleNumber','QC','ExpectedCN','Type')]), row.names=FALSE)
			} else if (all(is.na(std_mut_dfrm$ExpectedCN))) {
				cat(sprintf('WARNING: No expected copy numbers for any standards for mutant %s assay %s input %g source %s. Please check standard names for inference of expected CN. Cannot generate predictions for this standard group. Please see data analysis log file for additional details...\n',mut,assay,input,source))
			} else {
				cat(sprintf('Generating predictions...\n'))

				###############################
				# transformation for pred var #
				###############################

				x_orig <- std_mut_dfrm$ExpectedCN[which(!is.na(std_mut_dfrm$ExpectedCN) & std_mut_dfrm$QC == 'PASS')]
				x_trans <- get_x_trans(x_orig)

				###############################
				# transformation for resp var #
				###############################

				y_orig <- std_mut_dfrm$MTcount[which(!is.na(std_mut_dfrm$ExpectedCN) & std_mut_dfrm$QC == 'PASS')]
				# determine optimal lambda that maximizes correlation
				lambda_step <- 0.001
				lambda_min <- lambda_step
				lambda_max <- 20
				lambdas <- seq(lambda_min,lambda_max,lambda_step)
				lambda_list <- find_max_cor_lambda(x_trans,y_orig,lambdas)
				lambda <- lambda_list$lambda
				max_cor <- lambda_list$max_cor
				# save lambda and max_cor in stats file for each std group (in notes indicate mutation)
				stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Lambda',assay,input,source,std_group,'Standard',lambda,sprintf('Lambda that maximizes the linear correlation for mutation %s',mut))
				stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Maximum correlation',assay,input,source,std_group,'Standard',max_cor,sprintf('Maximum correlation value corresponding to selected lambda for mutation %s',mut))
				# perform Tukey transformation
				y_trans <- get_y_trans(y_orig,lambda)

				##############################
				# flags from transformations #
				##############################

				# determine flag for if lambda is on the boundary
				if (lambda == lambda_min | lambda == lambda_max) {
					exp_dfrm$FLAGS[mut_alt_ind] <- ifelse(is.na(exp_dfrm$FLAGS[mut_alt_ind]),'LB',paste(exp_dfrm$FLAGS[mut_alt_ind],';LB',sep=''))
					stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Boundary of lambda space',assay,input,source,std_group,'Standard',lambda,sprintf('Lambda is on the boundary of the search space for mutation %s',mut))
					cat(sprintf('WARNING: Lambda is on the boundary of the parameter space for mutant %s assay %s input %g source %s.  Still proceeding with generating predictions.  Please see data analysis log and stats files for additional details...\n',mut,assay,input,source))
				}

				######################
				# perform regression #
				######################

				# perform regression on transformed variables
				pr_dfrm <- data.frame(x=x_trans,y=y_trans)
				m <- rlm(y ~ x, pr_dfrm)
				coefs <- c(coef(m)[[1]],coef(m)[[2]])
				r2 <- (cor(pr_dfrm$x,pr_dfrm$y))^2
				eq <- substitute(italic(y) == a + b %.% italic(x)*", "~~italic(R)^2~"="~r2*', '~~lambda~'='~l,
									list(	a = format(coef(m)[1], digits = 3),
											b = format(coef(m)[2], digits = 3),
											r2 = format(r2, digits = 3),
											l = format(lambda, digits = 3)))
				eq <- as.character(as.expression(eq))
				# save R2 in stats file
				stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Intercept',assay,input,source,std_group,'Standard',coefs[1],sprintf('Intercept of regression for mutation %s',mut))
				stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Slope',assay,input,source,std_group,'Standard',coefs[2],sprintf('Slope of regression for mutation %s',mut))
				stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'R^2 value',assay,input,source,std_group,'Standard',r2,sprintf('R^2 value of regression for mutation %s',mut))

				#########################
				# flags from regression #
				#########################

				# determine flag for negative slope
				if (coefs[2] <= 0) {
					exp_dfrm$FLAGS[mut_alt_ind] <- ifelse(is.na(exp_dfrm$FLAGS[mut_alt_ind]),'NS',paste(exp_dfrm$FLAGS[mut_alt_ind],';NS',sep=''))
					stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Negative or zero slope of regression line',assay,input,source,std_group,'Standard',coefs[2],sprintf('Regression line has negative slope for mutation %s',mut))
					cat(sprintf('WARNING: Fitting produced a negative or zero slope for mutant %s assay %s input %g source %s.  Still proceeding with generating predictions.  Please see data analysis log and stats files for additional details...\n',mut,assay,input,source))
				}

				###################
				# plot regression #
				###################

				# save plot to exp_plot_list and save as one pdf after processing all exps
				p <- ggplot()
				p <- p + theme_bw()
				p <- p + theme(text = element_text(size=16))
				p <- p + stat_smooth(data=pr_dfrm, aes(x=x,y=y), method='rlm',fullrange=T,se=F)
				x <- seq(0,sqrt(max_std_expCN),0.02)
				pred_band_dfrm <- data.frame(x=x,lower=get_pred_band(x,coefs,pr_dfrm,'lower'),upper=get_pred_band(x,coefs,pr_dfrm,'upper'))
				p <- p + geom_line(data=pred_band_dfrm, aes(x=x,y=lower), color='blue', linetype='dashed')
				p <- p + geom_line(data=pred_band_dfrm, aes(x=x,y=upper), color='blue', linetype='dashed')
				# overlay points on lines
				p <- p + geom_point(data=pr_dfrm, aes(x=x,y=y), size=2, color='red', alpha=0.5)
				# alternative for specifying particular method, MM or M (default)
				#p <- p + stat_smooth(method=function(formula,data,weights=weight) rlm(formula, data, weights=weight, method="MM"), fullrange=TRUE)
				p <- p + annotate('text', x = min(pr_dfrm$x), y = max(pred_band_dfrm$upper), hjust=-0.1, vjust=1, label = eq, color="blue", size = 4, parse=TRUE)
				p <- p + labs(x=expression(sqrt(CN)), y=expression(mutant_reads^lambda), title=paste(runid,'\n','STD group ',std_group,': ',assay,', ',source,', ',mut,sep=''))
				i <- length(exp_plot_list)+1			# can have multiple plots from multiple mutations, but not guaranteed that all mutations will have STDs passing QC
				exp_plot_list[[i]] <- list()			# make a list so that we have flexibility to plot more for each unique exp/mut combo, e.g. lambda vs corr, etc.
				exp_plot_list[[i]] <- p

				########################
				# generate predictions #
				########################

				# generate predictions for this primary mutation and all alternate (non-primary) mutations, which should only happen for BRAF and Ex19del
				# NOTE: this will overwrite alt_muts if there are multiple prim_MT (currently not, 20161016)
				# SOLN: (if necessary in future) create a group column in bed files that indicates prim_MT group with all associated alt_MT
				to_predict <- get_y_trans(mut_alt_dfrm$MTcount,lambda)
				FitCN <- get_FitCN(to_predict,coefs)
				exp_dfrm$FitCN[mut_alt_ind] <- FitCN
				# statistics of individual standard levels
				std_levels <- sort(unique(std_mut_dfrm$ExpectedCN[which(!is.na(std_mut_dfrm$ExpectedCN) & std_mut_dfrm$QC == 'PASS')]))
				for (std_level in std_levels) {
					std_level_mut_dfrm <- exp_dfrm[which(exp_dfrm$MutationName == mut & exp_dfrm$Type == 'Standard' & exp_dfrm$QC == 'PASS' & exp_dfrm$ExpectedCN == std_level),]
					std_level_mean <- mean(std_level_mut_dfrm$FitCN,na.rm=T)
					std_level_sd <- sd(std_level_mut_dfrm$FitCN,na.rm=T)
					cv <- std_level_sd/std_level_mean*100
					stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'CV',assay,input,source,std_group,'Standard',cv,sprintf('CV for STD %d and mutation %s',std_level,mut))
					stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Mean',assay,input,source,std_group,'Standard',std_level_mean,sprintf('Mean for STD %d and mutation %s',std_level,mut))
					stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Std Dev',assay,input,source,std_group,'Standard',std_level_sd,sprintf('Standard deviation for STD %d and mutation %s',std_level,mut))
				}

				##################################
				# calculate prediction intervals #
				##################################

				FitCN_pred_int <- get_FitCN_pred_int(to_predict,coefs,pr_dfrm)
				exp_dfrm$FitCN_lower[mut_alt_ind] <- FitCN_pred_int$FitCN_lower
				exp_dfrm$FitCN_upper[mut_alt_ind] <- FitCN_pred_int$FitCN_upper

				##########################
				# translate to GEq units #
				##########################

				exp_dfrm$GEq[mut_alt_ind] <- get_GEq(exp_dfrm$FitCN[mut_alt_ind],exp_dfrm$ngPerRxn[mut_alt_ind])
				exp_dfrm$GEq_lower[mut_alt_ind] <- get_GEq(exp_dfrm$FitCN_lower[mut_alt_ind],exp_dfrm$ngPerRxn[mut_alt_ind])
				exp_dfrm$GEq_upper[mut_alt_ind] <- get_GEq(exp_dfrm$FitCN_upper[mut_alt_ind],exp_dfrm$ngPerRxn[mut_alt_ind])

				############################
				# determine detection call #
				############################

				if (perform_detection) {
					d <- std_mut_dfrm[which(!is.na(std_mut_dfrm$ExpectedCN) & std_mut_dfrm$QC == 'PASS'),]
					ds <- d %>% group_by(ExpectedCN) %>% summarise(MTcount_mean = mean(MTcount))
					upper_MTcount_mean <- ds$MTcount_mean[which(ds$ExpectedCN == lowest_nonzero_std_level)]
					lower_MTcount_mean <- ds$MTcount_mean[which(ds$ExpectedCN == 0)]

					if (upper_MTcount_mean - lower_MTcount_mean <= 0) {
						cat(sprintf('WARNING: Difference between STD0 mean and STD%d mean is less than or equal to 0.  Still proceeding with generating predictions.  Please see data analysis log for additional details...\n',lowest_nonzero_std_level,mut,assay,input,source))
					}
					exp_dfrm$bias_adj[mut_alt_ind] <- lower_MTcount_mean + dist_factor*(upper_MTcount_mean - lower_MTcount_mean)
					exp_dfrm$adj_mutant_reads[mut_alt_ind] <- exp_dfrm$MTcount[mut_alt_ind] - exp_dfrm$bias_adj[mut_alt_ind] + detection_threshold

					exp_dfrm$DetectionThreshold[mut_alt_ind] <- detection_threshold
					exp_dfrm$DetectCall[mut_alt_ind] <- ifelse(exp_dfrm$adj_mutant_reads[mut_alt_ind] >= detection_threshold,'Detected','Not Detected')
				}

				##########################
				# flags from predictions #
				##########################

				# determine flag for hot samples (defined as strictly greater than 30 percent above highest standard)
				mut_alt_hs_ind <- which((exp_dfrm$MutationName == mut | exp_dfrm$MutationName %in% alt_muts) & exp_dfrm$FitCN > hs_scalar*max_std_expCN)
				exp_dfrm$FLAGS[mut_alt_hs_ind] <- ifelse(is.na(exp_dfrm$FLAGS[mut_alt_hs_ind]),'HS',paste(exp_dfrm$FLAGS[mut_alt_hs_ind],';HS',sep=''))
				if (length(mut_alt_hs_ind) > 0) {
					cat(sprintf('WARNING: One or more hot samples for mutant %s assay %s input %g source %s.  Still proceeding with generating predictions.  Please see data analysis log for additional details...\n',mut,assay,input,source))
				}

				cat(sprintf('Finished generating predictions\n'))

				################
				# STD group QC #
				################

				# check that all anticipated STD levels are present and all appear in triplicate
				std_levels <- thres.wm$ExpectedCN[which(thres.wm$Assay == assay & thres.wm$Input == ifelse(source == 'U',60,10) & thres.wm$MutationName == mut)]
				sg_std_mut_dfrm <- exp_dfrm[which(exp_dfrm$MutationName == mut & exp_dfrm$Type == 'Standard'),]
				if (all(sg_std_mut_dfrm$ExpectedCN %in% std_levels) & all(unlist(lapply(std_levels, function(std_level) { nrow(sg_std_mut_dfrm[which(sg_std_mut_dfrm$ExpectedCN == std_level & !is.na(sg_std_mut_dfrm$FitCN)),]) == 3 })))) {
					cat(sprintf('Performing STD group QC...\n'))
					S.MAD <- mad(get_x_trans(sg_std_mut_dfrm$ExpectedCN)-get_x_trans(sg_std_mut_dfrm$FitCN))
					mut_sg_qc_fail <- F
					for (std_level in std_levels) {
						sg_qc_lb <- thres.wm[which(thres.wm$Assay == assay & thres.wm$Input == ifelse(source == 'U',60,10) & thres.wm$MutationName == mut & thres.wm$ExpectedCN == std_level),paste('lb.',std_group_qc_alpha,sep='')]
						sg_qc_ub <- thres.wm[which(thres.wm$Assay == assay & thres.wm$Input == ifelse(source == 'U',60,10) & thres.wm$MutationName == mut & thres.wm$ExpectedCN == std_level),paste('ub.',std_group_qc_alpha,sep='')]
						W.MAD <- thres.wm$W.MAD[which(thres.wm$Assay == assay & thres.wm$Input == ifelse(source == 'U',60,10) & thres.wm$MutationName == mut & thres.wm$ExpectedCN == std_level)]
						std_res <- (get_x_trans(sg_std_mut_dfrm$ExpectedCN[which(sg_std_mut_dfrm$ExpectedCN == std_level)])-get_x_trans(sg_std_mut_dfrm$FitCN[which(sg_std_mut_dfrm$ExpectedCN == std_level)]))/S.MAD
						pvals <- pnorm(std_res, mean=0, sd=sqrt(3)*W.MAD)
						pvals <- pmin(pvals,1-pvals)
						wm <- weighted.mean(std_res,pvals)

						if (wm < sg_qc_lb | wm > sg_qc_ub) {
							mut_sg_qc_fail <- T
							sg_qc_fail <- T
							cat(sprintf('WARNING: STD level %d failed for mutant %s assay %s input %g source %s.  Please see data analysis log for additional details...\n',std_level,mut,assay,input,source))
							# add row to stats file
							stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Weighted Mean',assay,input,source,std_group,'Standard',wm,sprintf('Weighted mean for STD %d and mutation %s',std_level,mut),'FAIL')
						} else {
							# add row to stats file
							stats_dfrm <- append_stats_dfrm(stats_dfrm,runid,'Weighted Mean',assay,input,source,std_group,'Standard',wm,sprintf('Weighted mean for STD %d and mutation %s',std_level,mut),'PASS')
						}
					}
					if (!mut_sg_qc_fail) {
						cat(sprintf('STD group passed QC for mutant %s assay %s input %g source %s.  Please see data analysis log for additional details...\n',mut,assay,input,source))
					}
					cat(sprintf('Finished STD group QC\n'))
				} else {
					cat(sprintf('WARNING: Cannot perform STD group QC due to either missing/extra STD levels or not all STD levels run in triplicate for mutant %s assay %s input %g source %s.\n',mut,assay,input,source))
				}
			}
		}

		cat(sprintf('Finished analyzing mutant %s\n\n',mut))
	}

	#######################
	# Finish STD group QC #
	#######################

	if (sg_qc_fail) {
		# set entire standard group to QC fail and append FLAGS with GQ
		# placement here is necessitated by KRAS to allow reads QC to be filtering criteria for fitting of subsequent mutants after one mutant fails STD group QC
		exp_dfrm$QC <- 'FAIL'
		exp_dfrm$FLAGS <- ifelse(is.na(exp_dfrm$FLAGS),'GQ',paste(exp_dfrm$FLAGS,';GQ',sep=''))
	}

	return(list(exp_dfrm=exp_dfrm,stats_dfrm=stats_dfrm,exp_plot_list=exp_plot_list))
}
