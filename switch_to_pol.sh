#!/bin/bash
COMMAND="cd ~/aye; git pull; checkout udp"
$($COMMAND)
ssh 172.24.1.91 $COMMAND
ssh 172.24.1.97 $COMMAND

bash
