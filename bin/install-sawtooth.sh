set -x

#1 install sawtooth
sudo rm -rf /etc/sawtooth/*
sudo rm -rf $HOME/.sawtooth/*
sudo rm -rf /var/lib/sawtooth/*
sudo mkdir -p /etc/sawtooth/keys

sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 8AA7AF1F1091A5FD
sudo add-apt-repository 'deb [arch=amd64] http://repo.sawtooth.me/ubuntu/chime/stable bionic universe'
sudo apt-get  update  -qq

sudo apt-get install -y --reinstall -qq sawtooth
sudo apt-get install -y --reinstall -qq sawtooth-pbft-engine
sudo apt-get install -y --reinstall -qq sawtooth-devmode-engine-rust

# (can view all packages with `dpkg -l '*sawtooth*'`)
# generate user key for sawtooth
sawtooth keygen --force my_key

# generate validator root key
sawadm keygen  # can add --force to overwrite existing, but we probably don't want this in case accidental rerun

sudo chmod 777 -R /etc/sawtooth/keys
sudo chmod 777 -R $HOME/.sawtooth/keys

cd /tmp
# this creates initial settings proposal batch that you are authorized to change since it uses your user private key
sawset genesis --key $HOME/.sawtooth/keys/my_key.priv

# For PBFT consensus genesis block, needs 4 nodes' public keys. Each node can broadcast their public key via <node-ip>:12222/pubkey.
sudo python3 /local/repository/src/api-decentralized-node.py &

## Start API


## INFO
#To delete the blockchain data, remove all files from /var/lib/sawtooth.
#To delete the Sawtooth logs, remove all files from /var/log/sawtooth/.
#To delete the Sawtooth keys, remove the key files /etc/sawtooth/keys/validator.\* and /home/yourname/.sawtooth/keys/yourname.\*.