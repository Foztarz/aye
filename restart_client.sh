#!/bin/bash
kill $(ps aux | grep "[p]ython" | awk '{print $2}')
sleep 1
python ~/aye/client.py
