#!/bin/bash

# DOES NOT WORK - something with grep failing but the tee line not actually unblocking, so it gets stuck there forever
# TODO fix

# see start-gnb.sh for partial technical explanation

set -x

upf() { sudo docker rm -f $(sudo docker ps -a -q) ; cd /z/oai-cn5g-fed/docker-compose/ && sudo docker-compose -f upf.yaml up -d && sudo docker logs -f oai-spgwu ; }
bad_log="Could not get response from NRF"

run_cmd_until_str_in_output() {
   # easiest to put command in one-liner function and pass function name (without $; add a semicolon at end of function)
   cmd=$1
   str="$2"
   # if grep spots the string in ouptut, it eventually crashes which kills the whole thing
   $cmd | tee >(stdbuf -o0 egrep "$str" >&- )
}

cd /local/repository/bin/
sudo bash gen-configs.sh
# necessary or packets will not be sent back through PDU tunnel interface tun0
sudo iptables -t nat -A POSTROUTING -o eno1 -j MASQUERADE
while [ 1 ]; do run_cmd_until_str_in_output upf "$bad_log" ; done

