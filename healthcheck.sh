#!bin/sh

"exit $(( (`date +%s` - `stat -L -c %Y /log/wp-mqtt.log` ) > 60 ))"
