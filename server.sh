#!/bin/bash
export WORKON_HOME=$HOME/.virtualenvs
. /usr/local/bin/virtualenvwrapper.sh
workon cv
python /home/pi/aye/server.py $1
bash
