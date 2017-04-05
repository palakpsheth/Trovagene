# returns the predicted copy number based on regression of transformed values
get_FitCN <- function(y_trans,coefs) {
	# NOTE: regression is backwards (pred/resp axes switched), so can't use predict function -- manually do backward prediction
	# y = c1 + c2*x => x = (y - c1)/c2
	trans_FitCN <- (y_trans - coefs[1])/coefs[2]	# manually do backward prediction
	trans_FitCN[which(trans_FitCN < 0)] <- 0		# if regression line has negative y-int, trans_FitCN may be negative (if lower than x-int) => set to 0
	FitCN <- get_x_inv_trans(trans_FitCN)			# perform inverse transformation to get actual FitCN
	return(FitCN)
}
