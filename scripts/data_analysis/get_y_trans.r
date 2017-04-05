# returns transformation of the y coordinates
get_y_trans <- function(orig_y,lambda) {
	trans_y <- orig_y^lambda
	return(trans_y)
}
