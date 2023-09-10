#!/bin/bash
source /local/repository/bin/typer.sh
typer "sudo RFSIMULATOR=127.0.0.1 /z/openairinterface5g/cmake_targets/ran_build/build/nr-uesoftmodem -r 106 \
--numerology 1 --band 78 -C 3619200000 --rfsim --sa --nokrnmod -d -O /local/repository/etc/ue.conf"
