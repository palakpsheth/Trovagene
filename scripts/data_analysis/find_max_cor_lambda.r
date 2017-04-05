# searches lambdas for maximal correlation between x and y
find_max_cor_lambda <- function(x, y, lambdas, plotit=F){
	r_lambdas <- unlist(lapply(lambdas, function(lambda, x, y){
		if(lambda == 0){
			y_lambda <- log(y)
		} else {
			y_lambda <- y^lambda
		}
		return(cor(x, y_lambda))
	}, x, y))

	lambda_hat <- lambdas[which.max(r_lambdas)]
	max_cor <- max(r_lambdas, na.rm=T)

	if (plotit == T) {
		plot(lambdas, r_lambdas)
	}
	return(list(lambdaHat=lambda_hat,max_cor=max_cor))
}
