#!/bin/bash

# explanation: runs the gNB, but uses tee to send output to both stdout (the screen) AND sends it to a grep command.
# The grep command is actually just used to match an error log that occurs in stderr when the gNB loses connection
# to the AMF and needs to be restarted to fix it (often this is due to restarting the AMF or entire control plane).
# If this line is matched, it will (eventually) cause the process to exit. Then you can just call this script with
# the following line to make it restart forever:

# while [ 1 ]; do cd /local/repository/bin/ && sudo bash start-gnb.sh ; done

# see https://superuser.com/questions/372886/kill-process-depending-on-its-stdout-output for more explanation

gnb() { cd /z/openairinterface5g/cmake_targets/ && sudo RFSIMULATOR=server ./ran_build/build/nr-softmodem --rfsim --sa -O /local/repository/etc/gnb.conf ; }
bad_log="Failed to find SCTP description for assoc_id"

run_cmd_until_str_in_output() {
   # easiest to put command in one-liner function and pass function name (without $; add a semicolon at end of function)
   cmd=$1
   str=$2
   # if grep spots the string in ouptut, it eventually crashes which kills the whole thing
   $cmd | tee >(stdbuf -o0 egrep $str >&- )
}

cd /local/repository/bin/ && sudo bash gen-configs.sh
while [ 1 ]; do run_cmd_until_str_in_output gnb $bad_log ; done

