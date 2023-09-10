#!/bin/bash

# kill all children processes when this script ends for whatever reason
# trap "exit" INT TERM
# trap "kill 0" EXIT

ue_existing_conf_filepath=$1
# warning - these are overwritten, but not deleted from UDM so junks up core DB
ue_conf_filepath="/tmp/testue.conf"
ue_binary_path="$HOME"
ue_binary_path="/z/openairinterface5g/cmake_targets"
altnetworking_cfg="/local/repository/etc/altnetworking.conf"
tls_results_file="/tmp/ue_tls_results"
# upf docker node address is 192.168.70.135
ue_interface="oaitun_ue1"

quiet=0

# generate random ue config and add to UDM core database
if [ $# -eq 0 ]
  then
    echo Missing one required argument: either a number 1-9 for node number for UE config generation and CP registration, or a filepath to an existing UE config file.
    exit 1
  else
    re='^[0-9]+$'
    if ! [[ $1 =~ $re ]] ; then
      # if not a number, treat argument as config filepath
      echo "using existing UE config at $ue_existing_conf_filepath"
      ue_conf_filepath=$ue_existing_conf_filepath
    else
      # if arg is a number, it specifies node number of UE config to route through
      echo "requesting core plane node to generate/register a UE config to test node $1's UPF:"
      sudo bash ./add-ue-to-cp.sh $ue_conf_filepath $1
    fi
fi

# start ue using config
cd $ue_binary_path
sudo RFSIMULATOR=127.0.0.1 ./ran_build/build/nr-uesoftmodem -r 106 --numerology 1 --band 78 -C 3619200000 --rfsim --sa --nokrnmod -O $ue_conf_filepath > /tmp/lastuetest.log 2>&1 &
ue_pid=$!

# works for 10 sometimes, but not always. Never works with 5 seconds
sleep 40

# have to update config or else default route wil be wrong and fail even if connectivity works
sudo sed -i 's/^desired_default_route=.*$/desired_default_route=12.1.'"$1"'.1/g' $altnetworking_cfg
# couldn't figure out better way to get results than put in file and read from file...
sudo /z/altnetworking/altnetworking.sh $altnetworking_cfg bash -c 'echo '' | openssl s_client -brief -connect google.com:443' &> $tls_results_file

# get rid of temp UE from core subscription info
tmpimsi=$(sudo cat /tmp/testue.conf | grep imsi | awk -F '"' '{print $2}')
sudo curl 10.10.1.1:18693/remove-ue/$tmpimsi


# kill the UE program
sudo pkill nr-ue
cat $tls_results_file
echo If UE connection worked, output will be between arrows:
echo "  |"
echo "  |"
echo "  v"
grep "Verification" $tls_results_file
echo "  ^"
echo "  |"
echo "  |"

rs=$(grep "Verification" $tls_results_file)
echo Result is "$rs; exiting..."

if [ -z "$rs" ] ; then
	exit 1
else
        if [[ "$rs" == "Verification: OK" ]] ; then
                exit 0
        fi
fi

exit 1
