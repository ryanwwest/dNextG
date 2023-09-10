# template substitution for various configs
cd /local/repository/src
sudo python3 templater.py res/upf-template.yaml /z/oai-cn5g-fed/docker-compose/upf.yaml
sudo python3 templater.py res/cp-template.yaml /z/oai-cn5g-fed/docker-compose/cp.yaml
sudo python3 templater.py res/gnb-template.conf /local/repository/etc/gnb.conf
sudo python3 templater.py res/validator-template.toml /etc/sawtooth/validator.toml
