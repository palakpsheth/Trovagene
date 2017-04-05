# parses config.ini
parse_config_file <- function(config_filename) { 
	conn <- file(config_filename)
	config_lines  <- readLines(conn)
	close(conn)

	# use '=' as separation character
	config_lines <- chartr("[]", "==", config_lines)

	connection <- textConnection(config_lines)
	d <- read.table(connection, as.is = TRUE, sep = "=", fill = TRUE)
	close(connection)

	# since headers brackets converted to '=', empty string in first field will indicate header, with list elements subsequent rows
	L <- d$V1 == ""
	d <- subset(transform(d, V3 = V2[which(L)[cumsum(L)]])[1:3], V1 != "")

	# build commands assigning list elements, to be evaluated afterwards
	config_options <- list()
	eval_commands <- paste("config_options$", d$V3, "$",  d$V1, " <- '", d$V2, "'", sep="")
	eval(parse(text=eval_commands))

	return(config_options)
} 
