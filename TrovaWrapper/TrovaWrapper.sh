#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR

python clia_run_daemon.py

python clia_analysis_daemon.py

python clia_archive_daemon.py
