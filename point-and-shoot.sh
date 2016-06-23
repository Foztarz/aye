#!/bin/bash
python ~/aye/panorama_image_producer.py &
ssh 172.24.1.91 python ~/aye/panorama_image_producer.py &
ssh 172.24.1.97 python ~/aye/panorama_image_producer.py &
ssh 172.24.1.118 python ~/aye/panorama_image_producer.py &
ssh 172.24.1.87 python ~/aye/panorama_image_producer.py &
ssh 172.24.1.137 python ~/aye/panorama_image_producer.py &

python panorama_orchestrator.py $1


