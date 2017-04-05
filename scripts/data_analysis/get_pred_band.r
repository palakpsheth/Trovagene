# returns values of either the lower or upper prediction band
get_pred_band <- function(x,coefs,pr_dfrm,band) {
	reg_line <- (coefs[1]+coefs[2]*x)
	pred_int <- qt(0.05/2, nrow(pr_dfrm)-2)*sqrt(sum((pr_dfrm$y - (coefs[1] + coefs[2]*pr_dfrm$x))^2)/(nrow(pr_dfrm)-2))*sqrt( 1+1/nrow(pr_dfrm)+((x-mean(pr_dfrm$x))^2)/sum((pr_dfrm$x-mean(pr_dfrm$x))^2) )
	if (band == 'lower') {
		pred_band <- reg_line + pred_int
	} else if (band == 'upper') {
		pred_band <- reg_line - pred_int
	} else {
		pred_band <- NA
	}
	return(pred_band)
}
