#!/bin/bash

log_path=$1
tty_path=`ls /dev/serial/by-id/*Zolertia_Firefly*` 
killall -9 picocom
killall -9 screen
screen -wipe
screen -dmS zoulscreen bash
screen -S zoulscreen -X stuff "picocom --noreset -fh -b 115200 --imap lfcrlf $tty_path | scripts/contiki-timestamp > $log_path\n"
sleep 1
ps | grep "$! "
exit $?
