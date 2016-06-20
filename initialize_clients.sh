#!/bin/bash
aye/stop_clients.sh

aye/start_client.sh &
ssh 172.24.1.91 aye/start_client.sh &
ssh 172.24.1.97 aye/start_client.sh &
