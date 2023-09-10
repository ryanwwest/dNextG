#!/usr/bin/env bash
set -x

if [[ "$(hostname -s)" == "node-0" ]] ; then
    echo node-0 centralized control plane core VNFs does not need sawtooth, skipping
    # should be in 5g, but in here it's run by the right user. to band-aid issue of control pane vnfs erroring out after ~80 min, have control plane restart every hour (causes a small cluster of failed tests).
    (crontab -l; echo '0 * * * * cd /local/repository/bin/ && sudo docker rm -f $(sudo docker ps -a -q); sudo docker system prune --force; sudo docker volume rm $(sudo docker volume ls -q); cd /z/oai-cn5g-fed/docker-compose/ && sudo docker-compose -f cp.yaml up -d') | sort -u | crontab -
    exit 0
fi

username=$(geni-get user_urn | grep -Eo '([^\+]+$)')
num_decentralized_nodes=$1


echo "User is $(whoami) (should not be root)"
# num_decentralized_nodes=$(cat /tmp/num_decentralized_nodes)
echo "There are $num_decentralized_nodes nodes."

#1 install sawtooth
sudo rm -rf /etc/sawtooth/*
sudo rm -rf $HOME/.sawtooth/*
sudo rm -rf /var/lib/sawtooth/*
sudo mkdir -p /etc/sawtooth/keys

# sawtooth is not running yet

sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 8AA7AF1F1091A5FD
sudo add-apt-repository 'deb [arch=amd64] http://repo.sawtooth.me/ubuntu/chime/stable bionic universe'
sudo apt-get  update  -qq

sudo apt-get install -y --reinstall -qq sawtooth
sudo apt-get install -y --reinstall -qq sawtooth-pbft-engine
sudo apt-get install -y --reinstall -qq sawtooth-devmode-engine-rust

# (can view all packages with dpkg -l '*sawtooth*')
# generate user key for sawtooth
sawtooth keygen --force my_key

# generate validator root key
sudo sawadm keygen --force # can add --force to overwrite existing, but we probably don't want this in case accidental rerun

sudo chmod 777 -R /etc/sawtooth/keys
sudo chmod 777 -R $HOME/.sawtooth/keys

cd /tmp
# this creates initial settings proposal batch that you are authorized to change since it uses your user private key
sawset genesis --key $HOME/.sawtooth/keys/my_key.priv



# this actually starts all of the nodes' validators and connects them as they become ready
if [[ "$(hostname -s)" != "node-0" ]] ; then
    # For PBFT consensus genesis block, needs 4 nodes' public keys. Each node can broadcast their public key via <node-ip>:12222/pubkey.
    sudo python3 /local/repository/src/api-decentralized-node.py > $HOME/api-decentralized-node.log 2>&1 &

    # designate node-1 to bootstrap after other nodes are ready
    if [[ "$(hostname -s)" == "node-1" ]] ; then
        echo "This is node-1, so will bootstrap sawtooth blockchain after all other nodes' pubkey APIs are ready."
        while :; do  # loop this forever (keep checking other nodes' API statuses) until inner loop succeeds (and thus exits)
            echo "Will check other nodes' statuses in 10 seconds..."
            sleep 10
            node_ip_final=1
            while [ $? -eq 0  ] ; do  # keep doing this loop as long as the final curl output is successful 
                if [[ $node_ip_final -gt $((num_decentralized_nodes)) ]] ; then 
                    echo "All decentralized nodes' pubkey APIs are online - bootstrapping blockchain from node-1."
                    cd /local/repository/bin && sudo bash setup-pbft.sh --bootstrap &
                    sleep 60
                    cd /local/repository/src && sudo python3 monitor.py | cat &>> $HOME/monitor.log 2>&1 & 
                    exit 0
                fi
                node_ip_final=$((node_ip_final+1))
                echo Testing if blockchain pubkey API is up for 10.10.1.$node_ip_final.
                curl -s 10.10.1.$node_ip_final:12222/pubkey  # this might have a bunch of output if there's an error, but we'd want to know abou the error
            done
        done
    else 
        echo "This decentralized node is not node-1, so starting decentralized API and will wait until node 1 has bootstrapped blockchain to join."

        $(exit 999) # used to set $? to nonzero for do-while loop ; this doesn't exit the script
        while [ $? -ne 0  ] ; do  # keep doing this loop as long as the final curl output is successful 
            sleep 15
            echo Testing every 15 seconds if node 1 sawtooth validator API is up for 10.10.1.2...
            curl -s 10.10.1.2:8008/status
            # the above curl must be the last command in this loop - if the service responds (even in error), curl 
            # returns 0 which means node-1 has successfully bootstrapped.
        done
        echo "node-1 sawtooth blockchain is UP, starting this node's validator..."
        cd /local/repository/bin && sudo bash setup-pbft.sh &
        sleep 60
        cd /local/repository/src && sudo python3 monitor.py > $HOME/monitor.log 2>&1 & 
    fi
fi

## INFO
#To delete the blockchain data, remove all files from /var/lib/sawtooth.
#To delete the Sawtooth logs, remove all files from /var/log/sawtooth/.
#To delete the Sawtooth keys, remove the key files /etc/sawtooth/keys/validator.\* and /home/yourname/.sawtooth/keys/yourname.\*.
