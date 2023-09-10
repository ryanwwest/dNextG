import subprocess
import sys
import time
from api_client import D5gBlockchainClient
import datetime
import random
from templater import get_node_number, get_num_decentralized_nodes

host_name = "0.0.0.0"
api_http_url = "http://127.0.0.1:8008"

# private_key_file = "/users/rww/.sawtooth/keys/my_key.priv"
# TODO delete, no point in opening public key if you can derive it from private
private_key_file = "/etc/sawtooth/keys/validator.priv"
public_key_file = "/users/rww/.sawtooth/keys/my_key.pub"
pk = None
vk = None
epic_history = {0: 0}

# Returns True if a simulated UE can successfully connect to the internet with HTTPS via a specific node's UPF.
def node_upf_connection_ok(nodeid, print_output=False):
    if print_output:
        print(f"Starting UE and testing connection through node-{nodeid} UPF, please wait...")
    test_cmd = f"cd /local/repository/bin && sudo bash testupf.sh {nodeid}"  # /local/repository/etc/ue-node{nodeid}.conf"
    try: 
        test_result = subprocess.run(test_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=100)
    except Exception as e:
        print(e)
        print(f"node-{nodeid} upf connection FAILED, timeout exceeded")
        return False
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
def test_and_report_node_upfs(nodeids, block_num):
    global vk
    debug_skip = False  # purely for debugging to quickly create txn
    if debug_skip:
        print("sending mock debug transaction")
        debug_txn_payload = {"nid": get_node_number(), "tested_nodes": {nid: True for nid in nodeids}, "seedblock": block_num, "timestamp": datetime.datetime.now().isoformat() }
        cli = D5gBlockchainClient(api_http_url, private_key_file)
        cli.send_transaction(debug_txn_payload)
        print(debug_txn_payload, "sent to api (should forward to tp)")
        return debug_txn_payload
    test_results = {}
    # todo parallelize testing multiple other nodes at once
    for nid in nodeids:
        retries = 2
        node_verified = False
        while retries >= 0:
            time.sleep(12)  # might help with node's gNB not accepting connections immediately after ended
            node_verified = node_upf_connection_ok(nid, print_output=True)
            # node_verified = True  # enable and comment out above line to bypass testing other nodes
            if node_verified:
                break
            retries -= 1
        test_results[nid] = node_verified

    if len(test_results) > 0:
        # only send reports for tested nodes
        txn_payload = { 
            "nid": get_node_number(),
            "tested_nodes": test_results,
            "seedblock": block_num,
            "timestamp": datetime.datetime.now().isoformat()
        }
        print(txn_payload)
        try: 
            cli = D5gBlockchainClient(api_http_url, private_key_file)
            out = cli.send_transaction(txn_payload)
        except Exception as e:
            print("Error: could not submit transaction to blockchain", e)
            return txn_payload
    else:
        raise Exception("No nodes were tested.")
    # caveat: if txn is rejected, this won't be updated
    return txn_payload

def get_current_block_num_hash():
    try:
        cli = D5gBlockchainClient(api_http_url, private_key_file)
        lb = cli.get_latest_block()
        print("current block num:", lb['header']['block_num'])
        print("current block hash:", lb['header']['state_root_hash'])
        return lb['header']['block_num'], lb['header']['state_root_hash']
    except Exception as e:
        print("error getting the latest block, so using default block 0, hash 0. Error:", e)
        return 0, 0


def get_verifiably_random_test_nodes(block_hash_seed, num_decentralized_nodes, this_nid):
    # this allows the random stream to be reproduced by others; includes this nid to avoid the same set across nodes
    random.seed(str(block_hash_seed) + str(this_nid)) 
    num_nodes_to_test_per_epic = 3 # cannot be more than 3 globally since minimum nodes in cluster is 4
    # all decentralized nodes besides this node are candidates for testing
    candidate_nids = list(range(1,num_decentralized_nodes+1))
    candidate_nids.remove(this_nid)
    # randomize the order of the candidates, then return the first X
    random.shuffle(candidate_nids)
    return candidate_nids[:num_nodes_to_test_per_epic]
    return list(map(str,candidate_nids[:num_nodes_to_test_per_epic]))

def monitor_up_traffic():
    epic = 1
    this_node_id = get_node_number()
    node_count = get_num_decentralized_nodes()
    last_block_num = 0
    while True:
        block_num, block_hash = get_current_block_num_hash()
        if int(last_block_num) == int(block_num):
            print(f"Warning: latest block number {block_num} has not changed - blockchain may not be updating")
        nodeids = get_verifiably_random_test_nodes(block_hash, node_count, this_node_id)
        print(f"there are {node_count} nodes, will test this set of nodes: {nodeids}")
        print(f"epoch: {epic} (host node and gNB: {this_node_id})")
        results = test_and_report_node_upfs(nodeids, block_num)
        epic_history[epic] = results
        epic += 1
        last_block_num = block_num
        time.sleep(180)

if __name__ == "__main__":
    monitor_up_traffic()
