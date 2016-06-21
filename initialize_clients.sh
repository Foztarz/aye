#!/bin/bash
~/aye/stop_clients.sh

~/aye/start_client.sh &
ssh 172.24.1.91 ~/aye/start_client.sh &
ssh 172.24.1.97 ~/aye/start_client.sh &
ssh 172.24.1.118 ~/aye/start_client.sh &
ssh 172.24.1.87 ~/aye/start_client.sh &
ssh 172.24.1.137 ~/aye/start_client.sh &
bash
