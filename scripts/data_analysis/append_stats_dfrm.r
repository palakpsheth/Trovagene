# appends a row to stats_dfrm
append_stats_dfrm <- function(stats_dfrm,runid,flag,assay,input,source,std_group,type,metric,comments,status=NA) {
	stats_dfrm <- rbind(stats_dfrm,
						data.frame( RunId=runid,
									Tool=unique(stats_dfrm$Tool),		# NOTE: the field 'Tool' needs to be unique!
									FLAG=flag,
									Assay=assay,
									Input=input,
									Source=source,
									StandardGroup=std_group,
									Type=type,
									Metric=metric,
									Comments=comments,
									Status=status))
	return(stats_dfrm)
}
