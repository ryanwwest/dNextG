set -x

cd /local/repository/src && sudo python3 templater.py res/validator-template.toml /etc/sawtooth/validator.toml $(cat /tmp/num_decentralized_nodes)
cd /tmp

members_str="["
mode="pbft"
username=$(geni-get user_urn | grep -Eo '([^\+]+$)')

# only bootstrap (create genesis block) if specifically trying to bootstrap with this node
if [[ "$1" == "--bootstrap" ]] ; then
    echo "Bootstrapping (creating genesis block for) this validator..."
    declare -A node_pubkeys

    node_ip_final=2
    node_pubkeys[$((node_ip_final-1))]=$(curl -s 10.10.1.$node_ip_final:12222/pubkey)
    # while the return code is 0 (curl returns the public key), keep going
    while [ $? -eq 0  ] ; do
        node_ip_final=$((node_ip_final+1))
        echo Trying to get pubkey from 10.10.1.$node_ip_final.
        node_pubkeys[$((node_ip_final-1))]=$(curl -s 10.10.1.$node_ip_final:12222/pubkey)
        # todo if one fails, then it gives up. Need better error handling for this
    done

    for i in "${!node_pubkeys[@]}"
    do
      if [ -n "${node_pubkeys[$i]}" ] ; then  # -n nonzero length str check
          echo "adding member key: $i, value: ${node_pubkeys[$i]}"
          members_str+="\"${node_pubkeys[$i]}\","
      else
          echo "key $i had no value, not adding to members"
      fi
    done
    members_str="${members_str::-1}]"

    # sawtooth set up
    sawset proposal create \
            --key $HOME/.sawtooth/keys/my_key.priv \
            sawtooth.consensus.algorithm.name=pbft \
            sawtooth.consensus.pbft.members="$members_str" \
            sawtooth.consensus.algorithm.version=1.0 -o config.batch
    # combine the 2 batches into 1 single genesis batch
    sudo -u sawtooth sawadm genesis config-genesis.batch config.batch
fi
if [[ "$1" == "--dev" ]] ; then
    mode="dev"
    echo "Running this validator in dev mode for debugging, will not connect to others..."
    cd /tmp
    # set consensus algorithm to devmode for debugging tp
    sawset proposal create \
            --key $HOME/.sawtooth/keys/my_key.priv \
            sawtooth.consensus.algorithm.name=Devmode \
            sawtooth.consensus.algorithm.version=0.1 -o config.batch
    sudo -u sawtooth sawadm genesis config-genesis.batch config.batch
fi

## Start the Validator (must start many background processes) ##
sudo -u sawtooth sawtooth-validator -v &
# start settings tp (transaction procesor) - not in instructions
sudo -u sawtooth settings-tp -v &

# make accessible on all interfaces for ease of evaluation
sudo -u sawtooth sawtooth-rest-api -v -B 0.0.0.0:8008 &

# start D5G tp
sudo python3 /local/repository/src/d5g_sawtooth_tp.py > /users/$username/d5g_sawtooth_tp.log 2>&1 &

if [[ $mode == "dev" ]] ; then
    # If intending to debug a transaction processor or other sawtooth thing, run the
    # below line. For some reason, running it here causes problems, and it only allows
    # catching the error once and then you have to rerun install-sawtooth.sh and 
    # setup-pbft.sh.
    #    sudo -u sawtooth devmode-engine-rust -vv --connect tcp://localhost:5050
    echo Do not forget to start devmode-engine-rust!!!
else
    sudo -u sawtooth pbft-engine -vv --connect tcp://localhost:5050 > /users/$username/pbft-engine.log 2>&1
fi
