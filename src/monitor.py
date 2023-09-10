import subprocess
import sys
import time
from api_client import D5gBlockchainClient
import datetime

host_name = "0.0.0.0"
api_http_url = "http://127.0.0.1:8008"

# private_key_file = "/users/rww/.sawtooth/keys/my_key.priv"
# TODO delete, no point in opening public key if you can derive it from private
private_key_file = "/etc/sawtooth/keys/validator.priv"
public_key_file = "/users/rww/.sawtooth/keys/my_key.pub"
pk = None
vk = None
epic_history = {0: 0}

def get_node_number():
    hostname = subprocess.getoutput("hostname -s")
    return int(hostname[-1])

# Returns True if a simulated UE can successfully connect to the internet with HTTPS via a specific node's UPF.
def node_upf_connection_ok(nodeid, print_output=False):
    if print_output:
        print(f"Starting UE and testing connection through node-{nodeid} UPF, please wait...")
    test_cmd = f"cd /local/repository/bin && sudo bash testupf.sh {nodeid}"  # /local/repository/etc/ue-node{nodeid}.conf"
    test_result = subprocess.run(test_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    is_verified = True if test_result.returncode == 0 else False
    if not print_output:
        return is_verified
    if  is_verified:
        print(f"node-{nodeid} upf connection verified.")
    else:
        # todo way to determine WHY it failed. Could be the gNB failed to connect, failed to PDU session, or bad certificate
        print(f"node-{nodeid} upf connection FAILED, exit code={test_result.returncode}")
    return is_verified

# todo should send all reports in one txn, not one txn per node
# todo support upf testing gnb
def test_and_report_node_upfs(nodeids): 
    global vk
    debug_skip = False  # purely for debugging to quickly create txn
    if debug_skip:
        print("sending mock debug transaction")
        debug_txn_payload = {"tested_nodes": {nid: True for nid in nodeids}}
        cli = D5gBlockchainClient(api_http_url, private_key_file)
        cli.send_transaction(debug_txn_payload)
        print(debug_txn_payload, "sent to api (should forward to tp)")
        return debug_txn_payload
    test_results = {}
    # todo parallelize testing multiple other nodes at once
    for nid in nodeids:
        retries = 1
        node_verified = False
        while retries >= 0:
            time.sleep(7)  # might help with node's gNB not accepting connections immediately after ended
            node_verified = node_upf_connection_ok(nid, print_output=True)
            # node_verified = True  # enable and comment out above line to bypass testing other nodes
            if node_verified:
                break
            retries -= 1
        test_results[nid] = node_verified
    
    if len(test_results) > 0:
        # only send reports for tested nodes
        txn_payload = { "tested_nodes": test_results, "timestamp": datetime.datetime.now().isoformat() }
        print(txn_payload)
        cli = D5gBlockchainClient(api_http_url, private_key_file)
        out = cli.send_transaction(txn_payload)
    else:
        raise Exception("No nodes were tested.")
    # caveat: if txn is rejected, this won't be updated
    return txn_payload


def monitor_up_traffic():
    epic = 1 
    this_node_id = get_node_number()
    while True:
        # todo allow arbitrary # nodes (but then design issue of n^2 messaging when
        #     scaling so maybe only do partial reputation reports then)
        nodeids = [1,2,3,4]  
        nodeids.remove(this_node_id)
        print(f"epoch: {epic} (host node and gNB: {this_node_id})")
        results = test_and_report_node_upfs(nodeids)
        epic_history[epic] = results
        epic += 1
        time.sleep(180)

if __name__ == "__main__":
    monitor_up_traffic()
