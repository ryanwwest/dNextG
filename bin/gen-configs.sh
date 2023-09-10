num_nodes=$1
if [[ $# -lt 1 ]] ; then
    echo 'usage: <number of decentralized nodes>'
    exit 1
fi
echo generating config files for a decentralized $num_nodes-node group

# template substitution for various configs
cd /local/repository/src
sudo python3 templater.py res/upf-template.yaml /z/oai-cn5g-fed/docker-compose/upf.yaml $num_nodes
sudo python3 templater.py res/cp-template.yaml /z/oai-cn5g-fed/docker-compose/cp.yaml $num_nodes
sudo python3 templater.py res/gnb-template.conf /local/repository/etc/gnb.conf $num_nodes
sudo python3 templater.py res/validator-template.toml /etc/sawtooth/validator.toml $num_nodes
sudo python3 templater.py res/smf-template.conf ../etc/smf.conf $num_nodes
