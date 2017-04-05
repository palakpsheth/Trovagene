# returns the prediction interval corresponding to values in y_trans
get_FitCN_pred_int <- function(y_trans,coefs,pr_dfrm) {
	# calculate prediction intervals 
	# equations:
	# MTp^lambda = (b0+b1*x0m) + t*s*sqrt( 1+1/n+((x0m-xbar)^2)/sum((xi-xbar)^2) )
	# MTp^lambda = (b0+b1*x0p) - t*s*sqrt( 1+1/n+((x0p-xbar)^2)/sum((xi-xbar)^2) )
	# solve for x0m and x0p
	
	n <- nrow(pr_dfrm)
	r <- mean(pr_dfrm$x)
	a <- coefs[1]
	b <- coefs[2]
	u <- sum((pr_dfrm$x-r)^2)
	se <- (pr_dfrm$y - (a + b*pr_dfrm$x))^2
	sse <- sum(se)
	s <- sqrt(sse/(n-2))
	alpha <- 0.05
	t <- qt(alpha/2, n-2)

	m <- y_trans

	aa <- n*u*b^2 - t^2*s^2*n
	bb <- -2*m*u*n*b + 2*n*a*b*u + 2*r*t^2*s^2*n
	cc <- n*u*m^2 + n*u*a^2 - 2*m*n*a*u - t^2*s^2*u*n - t^2*s^2*u - r^2*t^2*s^2*n
	x0m_1 <- (-bb + sqrt(bb^2 - 4*aa*cc))/(2*aa)	# upper
	x0m_2 <- (-bb - sqrt(bb^2 - 4*aa*cc))/(2*aa)	# lower

	# x0m_1 > x0m_2 by definition
	# should have x0m_1 >= 0 but check anyway
	x0m_2 <- ifelse(x0m_2 < 0,0,x0m_2)
	x0m_1 <- ifelse(x0m_1 < 0,0,x0m_1)

	# perform inverse transformation to get CN
	FitCN_lower <- get_x_inv_trans(x0m_2)
	FitCN_upper <- get_x_inv_trans(x0m_1)

	return(data.frame(FitCN_lower=FitCN_lower,FitCN_upper=FitCN_upper))
}
