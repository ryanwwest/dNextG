#!/bin/bash
set -x

cd /tmp

# todo possibly update in future. In 05-2022 this randomly started not working for a day, then worked the next day on all experiments
# gnb also needs to be restarted every ~10 UE connects
git clone --branch 2021.w46-powder --depth 1 https://gitlab.flux.utah.edu/powder-mirror/openairinterface5g /z/openairinterface5g

# apply patch so gNB will always expect UPF GTP tunnel to be at port 2152 even though gNB config sets itself to 2151,
#    so a gNB and UPF can run concurrently on same machine:
sudo sed -i --expression 's@^  tmp->outgoing_port=port;@  tmp->outgoing_port=2152; // port; RWW D5G patch - always use port 2152 for UPF and gNB config will be 2151 so they can run on same machine.@g' /z/openairinterface5g/openair3/ocp-gtpu/gtp_itf.cpp

cd /z/openairinterface5g
source oaienv
cd cmake_targets/

# Even if we won't be using USRP in this experiment, let's install UHD
export BUILD_UHD_FROM_SOURCE=True
export UHD_VERSION=3.15.0.0

# The next command takes around 8 minutes
# This command SHALL be done ONCE in the life of your server
./build_oai -I -w USRP

# Let's build now the gNB and nrUE soft modems
# The next command takes around 6 minutes
./build_oai --gNB --nrUE -w SIMU --build-lib nrscope --ninja

sudo cp -rf /opt/oai-cn5g-fed /z
#sudo mv /opt/openairinterface5g /z
sudo cp -rf /opt/altnetworking /z

sudo sysctl net.ipv4.conf.all.forwarding=1
sudo iptables -P FORWARD ACCEPT

sudo apt install -y python3-pip mysql-client-core-5.7

pip3 install Flask requests ecdsa

# for evaluations, not necessary for 5g
sudo apt install -y libjpeg-dev zlib1g-dev && sudo python3 -m pip install -U wheel matplotlib

# template substitution for various configs
cd /local/repository/src
sudo python3 templater.py res/upf-template.yaml /z/oai-cn5g-fed/docker-compose/upf.yaml
sudo python3 templater.py res/cp-template.yaml /z/oai-cn5g-fed/docker-compose/cp.yaml
sudo python3 templater.py res/gnb-template.conf /local/repository/etc/gnb.conf

# start ue gen api so other nodes can get ue configs to test
sudo python3 uegenapi.py &

# install script that forces application to use a specific ue interface
git clone https://github.com/ryanwwest/ezbik-scripts /tmp/ezbik-scripts
sudo mv /tmp/ezbik-scripts/altnetworking /z/altnetworking
# this command will not succeed but installs the dependencies necessary to run it later on
sudo /z/altnetworking/altnetworking.sh /local/repository/etc/altnetworking.conf bash -c 'ping google.com'

# clean up old running docker images. TODO build a clean image that doesn't have them running.
sudo docker rm -f $(sudo docker ps -a -q)


# don't run this, as we want to run the output of network topology algorithm
# cd /z/oai-cn5g-fed/docker-compose
# sudo python3 ./core-network.py --type start-basic --fqdn no --scenario 1
# sudo python3 ./core-network.py --type stop-basic --fqdn no --scenario 1

# can run sudo docker logs -f oai-amf to check if working here


# must run this separately for now when starting gnb and ue
# /share/powder/runvnc.sh &

# cd /z/openairinterface5g/cmake_targets
# sudo RFSIMULATOR=server ./ran_build/build/nr-softmodem --rfsim --sa -O /local/repository/etc/gnb.conf

# cd /z/openairinterface5g/cmake_targets
# sudo RFSIMULATOR=127.0.0.1 ./ran_build/build/nr-uesoftmodem -r 106 --numerology 1 --band 78 -C 3619200000 --rfsim --sa --nokrnmod -O /local/repository/etc/ue.conf


# generate traffic through 5g stack ping -I oaitun_ue1 192.168.70.135
# generate traffic directly to vnf (skip stack) ping -c 5 192.168.70.135
# see differnce in latency?

# get packet length on upf: sudo docker exec -it oai-spgwu  tshark -T fields -e frame.number -e ip.addr -e frame.len

# monitor gnb: python3 monitor.py 10 12345 "sudo tshark -i oaitun_ue1 -l -T fields -e frame.len"
# monitor gnb: python3 monitor.py 10 12346 "sudo docker exec -it oai-spgwu tshark -l -T fields -e frame.len"
