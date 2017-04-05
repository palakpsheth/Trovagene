#!/usr/bin/Rscript --vanilla

## Usage: Rscript generateCountPlots.R <_RAWCOUNTS.csv>

options(scipen=999)

#options(warn=-1)

suppressPackageStartupMessages(library(easyGgplot2))
suppressPackageStartupMessages(library(reshape2))
suppressPackageStartupMessages(library(tools))
suppressPackageStartupMessages(library(gridExtra))
#version <- R.version$minor
#if (as.numeric(version) >= 2.5) {
	suppressPackageStartupMessages(library(parallel))
#} else {
#	suppressPackageStartupMessages(library(multicore))
#}


args = commandArgs(trailingOnly=TRUE)
A = matrix(c("CSV files (*.csv)", "*.csv"), nrow=1, ncol=2, byrow = TRUE)   

if (interactive()) {
  args[1] <- choose.files(default="*_RAWCOUNTS.csv", multi=FALSE, caption = "Select RAWCOUNTS file", filters = A)
  mtName <- "c2573_G"
  wtName <- "c2573_T_WT"
  allName <- "c2573_ALL"
} else {
  args[1] <- file_path_as_absolute(args[1])
  mtName <- args[2]
  wtName <- args[3]
  allName <- args[4]
  if ( length(args) < 4 || length(args) > 4 ) {
    cat("mtName",mtName,sep=":",fill=TRUE)
    cat("wtName",wtName,sep=":",fill=TRUE)
    cat("allName",allName,sep=":",fill=TRUE)
    stop("Missing one of the following inputs: mtName wtName allName")
  }
}
basename <- basename(file_path_sans_ext(args[1]))
outFolder <- dirname(args[1])



# read in data
data <- read.csv(args[1],row.names = NULL, header=TRUE)
standards <- data[grep("std",data$Name,ignore.case = TRUE, perl = TRUE),]
standards10ng <- standards[grep("10",standards$Input,ignore.case = TRUE, perl = TRUE),]
standards10ng$MTcount <- standards10ng[[mtName]]
standards10ng$MT.WT <- standards10ng[[mtName]] / standards10ng[[wtName]]
standards10ng$MT.ALL <- standards10ng[[mtName]] / standards10ng[[allName]]

standards60ng <- standards[grep("60",standards$Input,ignore.case = TRUE, perl = TRUE),]
standards60ng$MTcount <- standards60ng[[mtName]]
standards60ng$MT.WT <- standards60ng[[mtName]] / standards60ng[[wtName]]
standards60ng$MT.ALL <- standards60ng[[mtName]] / standards60ng[[allName]]

cat(" ",fill=TRUE)

# define subfunctions
lm_eqn <- function(df,str,input){
	m <- lm(y ~ x, df)
	cat("== ",paste0(str,"_",input,"ng_lm_fit")," ==",fill=TRUE)
	cat("y =",format(coef(m)[1], digits = 3)," + ",paste0(format(coef(m)[2], digits = 3),"x"),fill=TRUE)
	cat("R-squared value = ",format(summary(m)$r.squared, digits = 3),fill=TRUE)
	test <- (format(summary(m)$residuals, digits=3))
	test <- as.numeric(test)
	testDF <- data.frame(residuals=test,row.names=NULL)
	cat("RESIDUALS:: ","Mean:",mean(test)," SD:",sd(test)," Median:",median(test)," MAD:",mad(test)," IQR:",IQR(test)," Min:",min(test)," Max:",max(test),"\n")
	cat(" ",fill=TRUE)
	eq <- substitute(italic(y) == a + b %.% italic(x)*","~~italic(r)^2~"="~r2, list(a = format(coef(m)[1], digits = 2), b = format(coef(m)[2], digits = 2), r2 = format(summary(m)$r.squared, digits = 3)))
	as.character(as.expression(eq))                
}

lm_eqn_BC <- function(df,str,input,lambdaHat){
  m <- lm(y ~ x, df)
  cat("== ",paste0(str,"_",input,"ng_BoxCox_lm_fit")," ==",fill=TRUE)
  cat("y =",format(coef(m)[1], digits = 3)," + ",paste0(format(coef(m)[2], digits = 3),"x"),fill=TRUE)
  cat("R-squared value = ",format(summary(m)$r.squared, digits = 3),fill=TRUE)
  cat("Mod. Box-Cox Lambda value = ",lambdaHat,fill=TRUE)
  test <- (format(summary(m)$residuals, digits=3))
  test <- as.numeric(test)
  testDF <- data.frame(residuals=test,row.names=NULL)
  cat("RESIDUALS:: ","Mean:",mean(test)," SD:",sd(test)," Median:",median(test)," MAD:",mad(test)," IQR:",IQR(test)," Min:",min(test)," Max:",max(test),"\n")
  cat(" ",fill=TRUE)
  eq <- substitute(italic(y) == a + b %.% italic(x)*","~~italic(r)^2~"="~r2*","~~italic(lambda)~"="~lambdaHat, list(a = format(coef(m)[1], digits = 2), b = format(coef(m)[2], digits = 2), r2 = format(summary(m)$r.squared, digits = 3), lambdaHat = format(lambdaHat, digits=3)))
  as.character(as.expression(eq))                
}

max.corr.lambda <- function(cp.num.sqrt, y, lambdas = seq(-1, 20, 0.01), plotit = F){
  r.lambdas <- unlist(mclapply(lambdas, function(lambda, cp.num, y){
    if(lambda == 0){
      y.lambda <- log(y)
    } else {
      y.lambda <- y^lambda
    }
    return(cor(cp.num, y.lambda))
  }, cp.num.sqrt, y))
  lambda.hat <- lambdas[which.max(r.lambdas)]
  #if(plotit == T | lambda.hat == min(lambdas) | lambda.hat == max(lambdas)){
  if(plotit == T){
    plot(lambdas, r.lambdas)
  }
  return(lambda.hat)
}

### LINEAR FIT FOR STDs using standard SLR and Box-Cox Transform
# do stuff for 10ng input if exists
if (nrow(standards10ng) > 1) {
	# FOR MTcount
	df <- data.frame(x=standards10ng$ExpectedCN,y=standards10ng$MTcount)
	label <- lm_eqn(df,"MTcount","10")
	#plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MTcount vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(mtName,"_mtCount"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=25,y=max(df$y),label=lm_eqn(df,"MTcount"),parse=TRUE)
	plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MTcount vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(mtName,"_mtCount"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df$x,na.rm=TRUE)*0.5),y=(max(df$y,na.rm=TRUE)*0.9),label=label,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MTcount.SLR.jpg"), plot=plot))
	
	lambdaHat <- max.corr.lambda(sqrt(df$x),df$y)
	newY <- (df$y)^lambdaHat
	dfBC <- data.frame(x=sqrt(df$x),y=newY)
	labelBC <- lm_eqn_BC(dfBC,"MTcount_BoxCox","10",lambdaHat)
	plotBC <- ggplot2.scatterplot(data=dfBC,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MTcount vs ExpectedCN Mod. Box-Cox Transform",xtitle="sqrt(ExpectedCN)",ytitle=paste0(mtName,"_mtCount^",lambdaHat),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(dfBC$x,na.rm=TRUE)*0.5),y=(max(dfBC$y,na.rm=TRUE)*0.9),label=labelBC,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MTcount.BoxCox.SLR.jpg"), plot=plotBC))
	
	#m <- lm(y ~ x, df)
	#bc <- boxcox(m, data=df)
	#trans <- bc$x[which.max(bc$y)]
	#df_BC <- data.frame(x=df$x,y=(df$y^trans))
	#label_BC <- lm_eqn_BC(df_BC,"MTcount_BoxCox_orig","10",trans)
	#plot_BC <- ggplot2.scatterplot(data=df_BC,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MTcount vs ExpectedCN Box-Cox Transform Original",xtitle="ExpectedCN",ytitle=paste0(mtName,"_mtCount^",trans),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df_BC$x,na.rm=TRUE)*0.5),y=(max(df_BC$y,na.rm=TRUE)*0.9),label=label_BC,parse=TRUE)
	
	suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MTcount.combined.SLR.jpg"), arrangeGrob(plot, plotBC), height=11, width=8.5, unit="in"))
	
	# FOR MT.WT
	df <- data.frame(x=standards10ng$ExpectedCN,y=standards10ng$MT.WT)
	label <- lm_eqn(df,"MT/WT","10")
	#plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MT/WT vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,wtName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=25,y=max(df$y),label=lm_eqn(df,"MT/WT"),parse=TRUE)
	plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MT/WT vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,wtName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df$x,na.rm=TRUE)*0.5),y=(max(df$y,na.rm=TRUE)*0.9),label=label,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MT.WT.SLR.jpg"), plot=plot))
	
	lambdaHat <- max.corr.lambda(sqrt(df$x),df$y)
	newY <- (df$y)^lambdaHat
	dfBC <- data.frame(x=sqrt(df$x),y=newY)
	labelBC <- lm_eqn_BC(dfBC,"MT/WT_BoxCox","10",lambdaHat)
	plotBC <- ggplot2.scatterplot(data=dfBC,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MT/WT vs ExpectedCN Mod. Box-Cox Transform",xtitle="sqrt(ExpectedCN)",ytitle=paste0(paste(mtName,wtName,sep="/"),"_ratio^",lambdaHat),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(dfBC$x,na.rm=TRUE)*0.5),y=(max(dfBC$y,na.rm=TRUE)*0.9),label=labelBC,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MT.WT.BoxCox.SLR.jpg"), plot=plotBC))
	
	suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MT.WT.combined.SLR.jpg"), arrangeGrob(plot, plotBC),height=11, width=8.5, unit="in"))
	
	# FOR MT.ALL
	df <- data.frame(x=standards10ng$ExpectedCN,y=standards10ng$MT.ALL)
	label <- lm_eqn(df,"MT/ALL","10")
	#plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MT/ALL vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,allName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=25,y=max(df$y),label=lm_eqn(df,"MT/ALL"),parse=TRUE)
	plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MT/ALL vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,allName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df$x,na.rm=TRUE)*0.5),y=(max(df$y,na.rm=TRUE)*0.9),label=label,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MT.ALL.SLR.jpg"), plot=plot))
	
	lambdaHat <- max.corr.lambda(sqrt(df$x),df$y)
	newY <- (df$y)^lambdaHat
	dfBC <- data.frame(x=sqrt(df$x),y=newY)
	labelBC <- lm_eqn_BC(dfBC,"MT/ALL_BoxCox","10",lambdaHat)
	plotBC <- ggplot2.scatterplot(data=dfBC,xName="x",yName="y", smoothingMethod="lm", mainTitle="10ng MT/ALL vs ExpectedCN Mod. Box-Cox Transform",xtitle="sqrt(ExpectedCN)",ytitle=paste0(paste(mtName,allName,sep="/"),"_ratio^",lambdaHat),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(dfBC$x,na.rm=TRUE)*0.5),y=(max(dfBC$y,na.rm=TRUE)*0.9),label=labelBC,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MT.ALL.BoxCox.SLR.jpg"), plot=plotBC))
	
	suppressMessages(ggsave(paste0(outFolder,"/",basename,"_10ng_MT.ALL.combined.SLR.jpg"), arrangeGrob(plot, plotBC),height=11, width=8.5, unit="in"))
}

# do stuff for 60ng input if exists
if (nrow(standards60ng) > 1) {
	# FOR MTcount
	df <- data.frame(x=standards60ng$ExpectedCN,y=standards60ng$MTcount)
	label <- lm_eqn(df,"MTcount","60")
	#plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MTcount vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(mtName,"_mtCount"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=25,y=max(df$y),label=lm_eqn(df,"MTcount"),parse=TRUE)
	plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MTcount vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(mtName,"_mtCount"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df$x,na.rm=TRUE)*0.5),y=(max(df$y,na.rm=TRUE)*0.9),label=label,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MTcount.SLR.jpg"), plot=plot))
	
	lambdaHat <- max.corr.lambda(sqrt(df$x),df$y)
	newY <- (df$y)^lambdaHat
	dfBC <- data.frame(x=sqrt(df$x),y=newY)
	labelBC <- lm_eqn_BC(dfBC,"MTcount_BoxCox","60",lambdaHat)
	plotBC <- ggplot2.scatterplot(data=dfBC,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MTcount vs ExpectedCN Mod. Box-Cox Transform",xtitle="sqrt(ExpectedCN)",ytitle=paste0(mtName,"_mtCount^",lambdaHat),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(dfBC$x,na.rm=TRUE)*0.5),y=(max(dfBC$y,na.rm=TRUE)*0.9),label=labelBC,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MTcount.BoxCox.SLR.jpg"), plot=plotBC))
	
	suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MTcount.combined.SLR.jpg"), arrangeGrob(plot, plotBC),height=11, width=8.5, unit="in"))
	
	# FOR MT.WT
	df <- data.frame(x=standards60ng$ExpectedCN,y=standards60ng$MT.WT)
	label <- lm_eqn(df,"MT/WT","60")
	#plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MT/WT vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,wtName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=25,y=max(df$y),label=lm_eqn(df,"MT/WT"),parse=TRUE)
	plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MT/WT vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,wtName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df$x,na.rm=TRUE)*0.5),y=(max(df$y,na.rm=TRUE)*0.9),label=label,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MT.WT.SLR.jpg"), plot=plot))
	
	lambdaHat <- max.corr.lambda(sqrt(df$x),df$y)
	newY <- (df$y)^lambdaHat
	dfBC <- data.frame(x=sqrt(df$x),y=newY)
	labelBC <- lm_eqn_BC(dfBC,"MT/WT_BoxCox","60",lambdaHat)
	plotBC <- ggplot2.scatterplot(data=dfBC,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MT/WT vs ExpectedCN Mod. Box-Cox Transform",xtitle="sqrt(ExpectedCN)",ytitle=paste0(paste(mtName,wtName,sep="/"),"_ratio^",lambdaHat),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(dfBC$x,na.rm=TRUE)*0.5),y=(max(dfBC$y,na.rm=TRUE)*0.9),label=labelBC,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MT.WT.BoxCox.SLR.jpg"), plot=plotBC))
	
	suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MT.WT.combined.SLR.jpg"), arrangeGrob(plot, plotBC),height=11, width=8.5, unit="in"))
	
	# FOR MT.ALL
	df <- data.frame(x=standards60ng$ExpectedCN,y=standards60ng$MT.ALL)
	label <- lm_eqn(df,"MT/ALL","60")
	#plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MT/ALL vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,allName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=25,y=max(df$y),label=lm_eqn(df,"MT/ALL"),parse=TRUE)
	plot <- ggplot2.scatterplot(data=df,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MT/ALL vs ExpectedCN",xtitle="ExpectedCN",ytitle=paste0(paste(mtName,allName,sep="/"),"_ratio"),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(df$x,na.rm=TRUE)*0.5),y=(max(df$y,na.rm=TRUE)*0.9),label=label,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MT.ALL.SLR.jpg"), plot=plot))
	
	lambdaHat <- max.corr.lambda(sqrt(df$x),df$y)
	newY <- (df$y)^lambdaHat
	dfBC <- data.frame(x=sqrt(df$x),y=newY)
	labelBC <- lm_eqn_BC(dfBC,"MT/ALL_BoxCox","60",lambdaHat)
	plotBC <- ggplot2.scatterplot(data=dfBC,xName="x",yName="y", smoothingMethod="lm", mainTitle="60ng MT/ALL vs ExpectedCN Mod. Box-Cox Transform",xtitle="sqrt(ExpectedCN)",ytitle=paste0(paste(mtName,allName,sep="/"),"_ratio^",lambdaHat),addRegLine = TRUE,addConfidenceInterval = TRUE) + geom_text(x=(max(dfBC$x,na.rm=TRUE)*0.5),y=(max(dfBC$y,na.rm=TRUE)*0.9),label=labelBC,parse=TRUE)
	#suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MT.ALL.BoxCox.SLR.jpg"), plot=plotBC))
	
	suppressMessages(ggsave(paste0(outFolder,"/",basename,"_60ng_MT.ALL.combined.SLR.jpg"), arrangeGrob(plot, plotBC),height=11, width=8.5, unit="in"))
}
