#!/bin/sh

#This script is intended for launch on *nix machines
#Xvfb :1 -screen 0 1920x1200x32 &
#export DISPLAY=":1"
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/

#-Xmx4000m indicates 4000 mb of memory, adjust number up or down as needed
#Script must be in the same directory as igv.jar
#Add the flag -Ddevelopment = true to use features still in development
prefix=`dirname $(readlink $0 || echo $0)`
exec xvfb-run --listen-tcp -a -s '-screen 0 1920x1200x16' java -Xmx16000m \
	-Dapple.laf.useScreenMenuBar=true \
	-Djava.net.preferIPv4Stack=true \
	-jar "$prefix"/igv.jar "$@"
