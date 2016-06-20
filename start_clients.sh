#!/bin/bash
aye/restart_client.sh &
ssh 172.24.1.91 aye/restart_client.sh &
ssh 172.24.1.97 aye/restart_client.sh &
bash
