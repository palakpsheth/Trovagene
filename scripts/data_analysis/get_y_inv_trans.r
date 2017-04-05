# returns the inverse transformation of the transformed y coordinates
get_y_inv_trans <- function(trans_y,lambda) {
	orig_y <- trans_y^(1/lambda)
	return(orig_y)
}
