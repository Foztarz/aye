#!/bin/bash
COMMAND="cd ~/aye; git pull; checkout simple-monitor"
$($COMMAND)
ssh 172.24.1.91 $COMMAND
ssh 172.24.1.97 $COMMAND
ssh 172.24.1.118 $COMMAND
ssh 172.24.1.87 $COMMAND
ssh 172.24.1.137 $COMMAND

bash
