from distutils.log import info
import sys
import subprocess
import time
from datetime import datetime, timedelta
from dateutil import parser
import threading
import multiprocessing
import json
import random
import matplotlib.pyplot as plt
import pickle

# This program represents a 'real' user's UE that connects to the D5G network.
#     It can both send and receive data regularly and periodically pull
#     reputation data from the network to determine the best path
#     to route through (or UPF to pick).

# WARNING:
# do not run this on a dNextG node, as it may conflict with the interfaces from its own monitor.py.
# instead, run this on node-0 or an extra node/UE if you added one. It shouldn't interfere with 5G core.

# using curl instead of python requests lib since curl easily specifies network interface

# globals - shared between threads
ue_start_time = 13
ue_stop_time = 13
g_cur_upf = 0

warn = "warn "
err = "error"
def log(msg, level="info "):
    curtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{curtime}] [{level.lower()}] [{threading.current_thread().name}] {msg}")

# is the interface that the PDU session runs up? normally oaitun_ueX
def is_iface_up(iface):
    iface_raw_output = subprocess.getoutput(f"ip addr | grep {iface}")
    if iface_raw_output is None:  # pdu session not started
        return False
    elif 'UNKNOWN' in iface_raw_output:  # PDU session working from this node POV
        return True
    # might otherwise look like this, which means pdu session not ready yet or failed
    # oaitun_ue1: <POINTOPOINT,MULTICAST,NOARP> mtu 1500 qdisc noop state DOWN group default qlen 500
    else:
        return False

def start_oai_ue_thread(gnb_node_num, upf_node_num):
    gnb_ip_addr = f"10.10.1.{gnb_node_num+1}"
    upf_ip_addr = f"10.10.1.{upf_node_num+1}"
    # using the default UE for the moment
    cfg_file = f"/local/repository/etc/ue-node{upf_node_num}.conf"
    log(f"starting UE, connecting to gNB at node {gnb_node_num} (IP address: {gnb_ip_addr}) and UPF at node {upf_node_num} (IP address: {upf_ip_addr})")
    output = subprocess.getoutput(f"sudo RFSIMULATOR={gnb_ip_addr} /z/openairinterface5g/cmake_targets/ran_build/build/nr-uesoftmodem -r 106 --numerology 1 --band 78 -C 3619200000 --rfsim --sa --nokrnmod -O {cfg_file}")
    end_output = "\n".join(output.splitlines()[-15:])
    log(f"UE process exiting... last 15 lines of output: \n{end_output}", warn)


def record_connection_data(attempts_data):
    start_ts = datetime.now()
    log("starting save")
    with open("persistent_ue_data.pickle", "wb") as f:
        pickle.dump(attempts_data, f)
    # plt.style.use('seaborn')
    plt.clf()
    plt.figure(figsize=(6, 4))
    plt.rcParams["figure.figsize"] = [7.00, 3.50]
    plt.rcParams["figure.autolayout"] = True


    colors = {'1': 'crimson', '2': 'blue', '3': 'green', '4': 'orange'}
    # generate the x data
    last10_cur = 0
    last10_points = []
    markers = []
    start_ts = attempts_data[0][2]
    for attempt in attempts_data:
        if attempt[1]: # if the attempt was successful, increment
            last10_cur += 1 
        else: 
            last10_cur -= 1 # if failed, decrement
        if last10_cur < 0:
            last10_cur = 0
        if last10_cur > 10:
            last10_cur = 10
        # last10_points.append(last10_cur)
        last10_points.append(attempt[0])
        markers.append("o" if attempt[1] else "x")
        ts = (attempt[2] - start_ts).total_seconds() / 60

        c = colors[str(attempt[0])] if attempt[1] else "black"
        plt.scatter(ts, attempt[0], color=c, marker="o" if attempt[1] else "x")

    # tss = [ (x[2] - start_ts).total_seconds() / 60 for x in attempts_data]
    plt.xlabel('Time (minutes)')
    plt.ylabel('Chosen UPF')
    # plt.ylim(2, 4)
    plt.yticks(ticks=[2,3,4], labels=[2, 3, 4])
    plt.legend()
    plt.savefig(f"persistent_ue_data.png")

    runtime = datetime.now() - start_ts
    if runtime > timedelta(milliseconds=500):
        log(f"saving connection data took {runtime}", level=warn)



# Will request each site every X seconds where X is frequency in seconds.
# Technically > X seconds since starts counting after all requests complete
# This also saves the data to a pickle and creates a matplotlib graph figure
def send_pdu_traffic_thread(pdu_iface, frequency, sites):
    # the PDU interface is by default oaitun_ueX where X is 1 unless multiple
    # UEs and PDU sessions are on the same machine concurrently.
    wait_time_between_check_iface = 10
    log("starting traffic thread")
    attempt_num = 100
    last_100_attempts = [] # actually 10
    while True:
        while is_iface_up(pdu_iface):
            for site in sites:
                # any reason to log/check output?
                # 20mb file might need curl?? idk
                try:
                    subprocess.getoutput(f"curl {site} --output /dev/null --interface {pdu_iface}")
                except Exception:
                    log(f"failed to connect on PDU interface {pdu_iface}", warn)
                    break
            time.sleep(frequency)
            last_100_attempts.append((g_cur_upf, True, datetime.now()))
            # if len(last_100_attempts) > attempt_num:
                # del last_100_attempts[0]
            percentage = sum(j for _, j, _ in last_100_attempts[:attempt_num]) / min(attempt_num, len(last_100_attempts))
            log(f"contacted {len(sites)} sites via PDU interface {pdu_iface} and UPF {g_cur_upf}. Success rate (last {attempt_num}): {(percentage*100):.2f}%")
            record_connection_data(last_100_attempts)
        last_100_attempts.append((g_cur_upf, False, datetime.now()))
        # if len(last_100_attempts) >= attempt_num:
            # del last_100_attempts[0]
        percentage = sum(j for _, j, _ in last_100_attempts[:attempt_num]) / min(attempt_num, len(last_100_attempts))
        log(f"interface {pdu_iface} not up for UPF {g_cur_upf}, will recheck in {wait_time_between_check_iface} seconds. Success rate (last {attempt_num}): {(percentage*100):.2f}%", warn)
        record_connection_data(last_100_attempts)
        time.sleep(wait_time_between_check_iface)

def get_best_upf_nids(reputations, latencies, cur_gnb):
    if reputations is None:
        return None, None
    # todo latency
    best_nids = []
    while len(best_nids) == 0:
        best_rep_val = max(reputations.items(), key=lambda x : x[1])[1]
        for key, val in reputations.items():
                if val == best_rep_val:
                    best_nids.append(key)
        if str(cur_gnb) in best_nids:
            best_nids.remove(str(cur_gnb))
        if len(best_nids) == 0:
            del reputations[str(cur_gnb)]
            log(f"best node {cur_gnb} is already used by UPF, pick next best")
        return best_nids, best_rep_val

# attempt contact all nodes in info_source_nodes and cross check that they return identical. If 
# there are discrepencies, log them. Then return the results of the first node contacted
def fetch_network_state(info_source_nodes, pdu_iface, gnb_node_num, cur_upf):
    shared_reputation = None
    found_discrepancies = False
    nodes_successfully_contacted = 0
    error_char_print_num = 400
    log(f"Starting to fetch network state for reputation evaluation through UPF node {cur_upf} and gNB node {gnb_node_num}...")
    for nid in info_source_nodes:
        node_ip_port = f"10.10.1.{nid+1}:12222"
        rj = None
        lj = None
        try: 
            latencies = subprocess.check_output(f"curl --interface {pdu_iface} {node_ip_port}/network_latency", shell=True, stderr=subprocess.DEVNULL, timeout=10)
            reputation = subprocess.check_output(f"curl --interface {pdu_iface} {node_ip_port}/network_reputation", shell=True, stderr=subprocess.DEVNULL, timeout=10)
        except subprocess.TimeoutExpired:
            log(f"could not contact dNextG API of {nid} through gnb node {gnb_node_num} and upf {cur_upf}, curl timeout expired", warn)
            continue
        except Exception as e:
            curl_exit_code = str(e)[-3:-1]
            printed = False
            try: 
                code = int(curl_exit_code)
                if code == 45:
                    log(f"interface {pdu_iface} down; could not contact dNextG API of {nid} through gnb node {gnb_node_num} and upf {cur_upf}", warn)
                    printed = True
                elif code == 7:
                    log(f"could not contact dNextG API of {nid}; connection up but API server unresponsive")
                    printed = True
            except Exception:
                pass
            if not printed:
                log(f"could not contact dNextG API of {nid} through gnb node {gnb_node_num} and upf {cur_upf}: {e}")
            continue
        try: 
            lj = json.loads(latencies.decode('utf-8'))
        except Exception:
            lprintpart = latencies[-error_char_print_num:] if len(latencies) > error_char_print_num else latencies
            log(f"Error parsing node {nid}'s dNextG API /network_latency response, start of response: {lprintpart}")
        try:
            rj = json.loads(reputation.decode('utf-8'))
        except Exception:
            rprintpart = reputation[-error_char_print_num:] if len(reputation) > error_char_print_num else reputation
            log(f"Error parsing node {nid}'s dNextG API /network_reputation response, start of response: {rprintpart}")
        # TODO also check node latency discrepancies between nodes somehow
        if shared_reputation is None:
            shared_reputation = rj
        elif shared_reputation != rj and rj is not None:
            found_discrepancies = True
            # note that this happens if state happens to change between checking all nodes. This type 
            # of discrepancy should result in just repeating the checks.
            log(f"DISCREPANCY DETECTED in reputations between node 1 and {nid}: ", warn)
            log(f"node 1 reputation: {shared_reputation}", warn)
            log(f"node {nid} reputation: {rj}", warn)
        nodes_successfully_contacted += 1

    log(f"contacted {nodes_successfully_contacted} nodes")
    if found_discrepancies:
        log("discrepancies were found in this check")
    elif rj is not None:
        log(f"no discrepancies found; reputations: { { elem[0]: round(elem[1], 2) for elem in rj.items() } }")

    return rj, lj

# use the DNextG blockchain state and latency information to choose the best network path for the UE
# pdu_iface: what linux network interface to use for PDU session connection
# info_source_nodes: list of node ids (nids) to redundantly check for blockchain/latency info. more
#     checks gives greater confidence (could catch a lying node)
def evaluate_network_state_thread(pdu_iface, info_source_nodes, gnb_node_num, cur_upf):
    # should be able to use any dnextg ue_blockchain_api to get the data. could get from multiple nodes
    # to increase confidence of correctness / nodes not reporting false information
    global g_cur_upf
    log("starting network evaluation thread")
    log(f"will fetch network state from these nodes: {info_source_nodes}")
    time_between_evaluations = 20
    cur_ue_conn_fails = 0
    max_ue_fails = 2

    # must start UE thread here in order to restart when highest reputation node changes
    ueproc = multiprocessing.Process(name="UE", target=start_oai_ue_thread, args=(gnb_node_num, cur_upf))
    ueproc.start()
    time.sleep(ue_start_time)
    last_best_upf_nids = None
    no_best_upf_cur_nid_attempt = 1
    num_network_nodes = 4

    while True:
        rep, lat = fetch_network_state(info_source_nodes, pdu_iface, 
            gnb_node_num, cur_upf)
        
        # now determine best upf and reroute UE through a better one if necessary
        best_nids, best_rep = get_best_upf_nids(rep, lat, gnb_node_num)
        log(f"best nodes for UPF (reputation value {best_rep}): {best_nids}")

        if best_nids is None or len(best_nids) == 0:
            cur_ue_conn_fails += 1
        else:
            last_best_upf_nids = best_nids
            cur_ue_conn_fails = 0

        # if there's a problem, may need to restart and reconfigure UE
        if not ueproc.is_alive() or (best_nids is not None and str(cur_upf) not in best_nids) or max_ue_fails <= cur_ue_conn_fails:
            if not ueproc.is_alive():
                log("UE process exited, so restarting it")
            # if the last attempt to contact any node API failed, use the last good one, or try everything if no cache
            if best_nids is None or len(best_nids) == 0:
                log("restarting UE to connect through a higher reputation UPF node")
                if last_best_upf_nids is None:
                    if no_best_upf_cur_nid_attempt == gnb_node_num:
                        no_best_upf_cur_nid_attempt += 1
                    best_nids = [no_best_upf_cur_nid_attempt]
                    # todo might be better to have UE detect if gNB is instead failing
                    log(f"no cache of best reputation UPF nodes, so trying node {no_best_upf_cur_nid_attempt}")
                    no_best_upf_cur_nid_attempt += 1
                    if no_best_upf_cur_nid_attempt > num_network_nodes:
                        no_best_upf_cur_nid_attempt = 1
                else: 
                    log(f"using locally cached last best reputation UPF nodes; deleting cache...")
                    best_nids = last_best_upf_nids
                    last_best_upf_nids = None
                cur_ue_conn_fails = 0
            chosen_nid = random.choice(best_nids)
            if max_ue_fails <= cur_ue_conn_fails:
                log(f"restarting UE because of {max_ue_fails} repeated connection failures to 5G core")
            if chosen_nid != cur_upf:
                log(f"reconfiguring and restarting UE to connect through higher reputation node {chosen_nid}'s UPF instead of current node {cur_upf}")
            else:
                log(f"restarting UE to connect through same node {chosen_nid}'s UPF")
            cur_upf = int(chosen_nid)
            g_cur_upf = cur_upf
            ueproc.terminate()
            time.sleep(ue_stop_time)
            ueproc = multiprocessing.Process(name="UE", target=start_oai_ue_thread, args=(gnb_node_num, cur_upf))
            ueproc.start()
            time.sleep(ue_start_time)

        time.sleep(time_between_evaluations)


def main():
    args = sys.argv
    # uncomment for command line control
    #if len(args) != 2 + 1:
    #    print('Usage: <gnb node> <upf node>')
    #    exit(1)

    iface_name = "oaitun_ue1"  # for local, todo allow multiple concurrent i.e. oaitun_ue2
    gnb_node_num = 1 #int(args[1])
    upf_node_num = 2 #int(args[2])
    global g_cur_upf
    g_cur_upf = upf_node_num
    # todo don't asssume 4 node decentralized network
    evaluate_source_node_nums = [1,2,3,4]

    # create all threads
    threads = []
    eval_thread = threading.Thread(name="Net Eval", target=evaluate_network_state_thread, args=(iface_name,
    evaluate_source_node_nums, gnb_node_num, upf_node_num))
    eval_thread.start()
    time.sleep(ue_start_time)
    traffic_thread = threading.Thread(name="UE traffic", target=send_pdu_traffic_thread,
        args=(iface_name, 8, ["https://example.com"]))#, "http://ipv4.download.thinkbroadband.com/1MB.zip"]))
    threads.append(traffic_thread)
    traffic_thread.start()
    threads.append(eval_thread)

    # wait for all threads to complete before exiting
    for thread in threads:
        thread.join()
    log("finished all threads, exiting...")

if __name__ == "__main__":
    main()
