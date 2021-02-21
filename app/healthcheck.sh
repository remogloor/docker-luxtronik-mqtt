#!/bin/sh

exit $(( (`date +%s` - `stat -L -c %Y /log/wp-mqtt-status.log` ) > 60 ))
