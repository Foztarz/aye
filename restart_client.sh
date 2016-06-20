#!/bin/bash
kill $(ps aux | grep python | awk '{print $2}')
sleep 1
python ~/aye/client.py
