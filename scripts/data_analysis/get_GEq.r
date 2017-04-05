# converts FitCN to GEq for a sample with input ngPerRxn
get_GEq <- function(FitCN,ngPerRxn) {
	GEq <- FitCN * 1e5 / (303 * ngPerRxn)
	return(GEq)
}
