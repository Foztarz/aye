#!/bin/bash
python aye/restart_client &
ssh 172.24.1.91 python aye/restart_client.sh &
ssh 172.24.1.97 python aye/restart_client.sh &
bash
