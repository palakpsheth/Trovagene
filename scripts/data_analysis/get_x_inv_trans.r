# returns the inverse transformation of the transformed x coordinates
get_x_inv_trans <- function(trans_x) {
	orig_x <- trans_x^2
	return(orig_x)
}
