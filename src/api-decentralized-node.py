import subprocess
from flask import Flask
from webbrowser import get
from api_client import D5gBlockchainClient
from tp.d5g_payload import D5gUpPayload
import requests
import json
from templater import get_node_number, get_num_decentralized_nodes

app = Flask(__name__)

validator_pubkey_filepath = "/etc/sawtooth/keys/validator.pub"

all_node_pubkeys = None

network_node_count = 4

api_http_url = "http://127.0.0.1:8008"
private_key_file = "/etc/sawtooth/keys/validator.priv"

# measures the latency to all other nodes in network
def measure_network_latency(number_of_nodes):
    latencies = {}
    for i in range(number_of_nodes):
        node_addr = f"10.10.1.{i+2}"
        pingstr = subprocess.getoutput(f"ping {node_addr} -c1 | grep -Po \"time.*\"")
        ping = float(pingstr[5:].partition(' ')[0])
        latencies[i+1] = ping
    return latencies

# pull latest blockdata from blockchain layer
def get_blockchain_data(pubkeys):
    cli = D5gBlockchainClient(api_http_url, private_key_file)
    # todo add signature validation to keep make it more difficult for node to lie?
    avg_node_reps = {str(x): 0 for x in range(1,network_node_count+1)}
    avg_count = 0
    for nid, pubkey in pubkeys.items():
        try:
            txnbytes = cli.get_txn(pubkey, nid)
            node_observed_reputations = json.loads(txnbytes)
            print('debugnid', nid, node_observed_reputations)
            for obs_nid, rep in node_observed_reputations.items():
                if str(obs_nid) == str(nid):  # don't count nodes self reputation report
                    print('skipit', obs_nid)
                    continue
                avg_node_reps[obs_nid] += rep
            avg_count += 1
        except Exception as e:
            print(f'caught exception while contacting node {nid}: {e}')
            continue
    for nid in avg_node_reps:
        avg_node_reps[nid] /= avg_count-1  # subtract one to account for node's own self
    print(avg_node_reps)
    return avg_node_reps


# includes reputation and latency info
@app.route("/network_reputation", methods=['GET'])
def get_network_reputation():
    global all_node_pubkeys
    if all_node_pubkeys is None:
        all_node_pubkeys = get_all_node_pubkeys(network_node_count)
    return get_blockchain_data(all_node_pubkeys)

# node tests all other nodes for latency checks
@app.route("/network_latency", methods=['GET'])
def get_network_latencies():
    return measure_network_latency(network_node_count)

# get the public key of node running this API.
@app.route("/pubkey", methods=['GET'])
def get_node_pubkey():
    global all_node_pubkeys
    with open(validator_pubkey_filepath) as f:
        pubkey = f.readlines()[0]
        print(pubkey)
        return pubkey

def get_all_node_pubkeys(number_of_nodes):
    global all_node_pubkeys
    pubkeys = {}
    this_node = get_node_number()
    for i in range(number_of_nodes):
        if i+1 == this_node:
            pubkeys[i+1] = str(get_node_pubkey()).strip()
            continue
        node_addr = f"10.10.1.{i+2}"
        response = requests.get(f"http://{node_addr}:12222/pubkey")
        pubkeys[i+1] = response.text.strip()
    print(pubkeys)
    return pubkeys


if __name__ == '__main__':
    network_node_count = get_num_decentralized_nodes()
    app.run(host="0.0.0.0", port=12222, debug=True)
