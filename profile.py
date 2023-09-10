#!/usr/bin/python

import geni.portal as portal
import geni.urn as URN
import geni.rspec.pg as rspec
import geni.rspec.emulab.pnext as PN
import geni.rspec.igext as IG

scripts_dir = "/local/repository/bin/"

def invoke_script_str(filename, args_str, sudo=False):
    # populate script config before running scripts (replace '?'s)
    #populate_config = "sed -i 's/NUM_UE_=?/NUM_UE_=" + str(params.uenum) + "/' " + GLOBALS.SCRIPT_DIR+GLOBALS.SCRIPT_CONFIG
    #populate_config2 = "sed -i 's/UERANSIM_BRANCHTAG_=?/UERANSIM_BRANCHTAG_=" + str(params.ueransim_branchtag) + "/' " + GLOBALS.SCRIPT_DIR+GLOBALS.SCRIPT_CONFIG
    # also redirect all output to /script_output
    run_script = "bash " + scripts_dir + filename + " " + args_str + " &> ~/" + filename + ".log"
    if sudo:
        run_script = "sudo " + run_script
    #return populate_config + " && " + populate_config2 + " && " +  run_script
    return run_script

pc = portal.context
request = pc.makeRequestRSpec()

# Parameters
pc.defineParameter("phystype",  "Optional physical node type",
                   portal.ParameterType.STRING, "d430",
                   longDescription="Specify a physical node type (e.g., d430, d740, d840; NOT d820 or d710) " +
                   "instead of letting the resource mapper choose for you.")
pc.defineParameter("phystype_array",  "Optional physical node type for every node",
                   portal.ParameterType.STRING, "",
                   longDescription="In case of node unavailability using one type, can specify multiple types in comma-separated order node-0,node-1,... here (example: d430,d430,d430,d430,d740).")
pc.defineParameter(
    "nodeCount","Number of Nodes",
    portal.ParameterType.INTEGER,5,
    min=5, max=255,
    longDescription="Number of nodes to spin up, all with the same installations. All but one of these will be decentralized nodes; 10.10.1.1 is always the centralized 5G Core (control plane) node.")
params = pc.bindParameters()
pc.verifyParameters()

link = request.Link("link")
if params.phystype_array is not '':
    node_types = params.phystype_array.split(',')
for i in range(0,params.nodeCount):
    nodename = "node-%d" % (i,)
    node = request.RawPC(nodename)
    node.disk_image = "urn:publicid:IDN+emulab.net+image+PowderSandbox:d5g.node"
    if len(params.phystype_array.split(',')) > i:
        node.hardware_type = params.phystype_array.split(',')[i]
    else:
        node.hardware_type = "d430" if params.phystype == "" else params.phystype
    
    dnodes = params.nodeCount - 1
    node.addService(rspec.Execute(shell="bash", command=invoke_script_str("install-5g.sh", str(dnodes), sudo=True)))
    node.addService(rspec.Execute(shell="bash", command=invoke_script_str("install-sawtooth.sh", str(dnodes))))
    bs = node.Blockstore("bs{}".format(i), "/z")
    bs.size = "60GB"
    link.addNode(node)


# README info

# node 0 being the centralized node cannot easily change as 10.10.1.1 is hardcoded in many areas
tourDescription = """
# dNextG: A Zero-Trust Decentralized Mobile Network User Plane (also known as D5G in this 5G prototype)

This profile instantiates an experiment that runs a simulated 5G RAN and Core network on Docker, along with a Hyperledger Sawtooth validator node and an Orchestrator program that sits between them. It will eventually include several nodes.

This implementation uses 4 or more decentralized nodes (nodes 1-4+), which is the minimum number of nodes required for PBFT and also the maximum number of DNNs supported by OAI (in the version used). Each of these nodes runs a gNB, a UPF, a Hyperledger Sawtooth blockchain Validator, and various reputation scripts. There is also one 5G Core control plane node, node-0, which runs the AMF, SMF, AUSF, UDM, UDR, and NRF.

If you want to experiment with an automatically configured setup, use the `master` branch when instantiating an experiment, which will set up simulated gNBs and UEs. The `cots-ue` branch instantiates real COTS UEs and gNBs if you have reserved proper spectrum during the experiment time, but its setup is *not* automated using the steps below and is not ready for easy experimentation.
"""

tourInstructions = """
Node 0 is the centralized node running the 5G Core, and all remaining nodes are decentralized nodes running gNBs, UPFs, and dNextG processes. When the paper was submitted for publication in 2023-06, this POWDER experiment would automatically run scripts `bin/install-5g.sh` and `bin/install-sawtooth.sh` which installed the 5G core on node 0, UPFs and gNBs and Sawtooth validators on all remaining nodes, and automatically started and connected all of these processes together and started the dNextG reputation system. As OAI and Hyperledger frequently update their software versions/URLs, these scripts are prone to breakage with time and may need tweaks - the output logs of these automatically-run scripts are found in the home directory.

The easiest way to check the dNextG reputation state (on the Hyperledger Sawtooth ledger) is by running the following command on any decentralized node (any node except node-0):
```
sudo sawtooth block list | head -2 && sudo sawtooth transaction list | head | grep --only-matching "'{.*$"
```

Each row (starting at the third line of output) represents a psuedo-UE test result of a node that tested 3 other nodes by their node IDs. If all test results are 'false', then all reputation tests are failing which could indicate something is wrong with the 5G Core (on node-0) - check the docker logs of the Core VNFs running on node-0 (and if no containers are running/created, see if the install script failed by looking at its logs at ~/install-sawtooth.sh.log). If the tests of only one particular node id (or 'nid') tests are failing, this could indicate a problem with the UPF or gNB of that node - the UPF can also be checked with docker and the gNB PID status can be checked with `ps aux | grep nr-softmodem`. The autorun install scripts provide the best indications of how to (re)start any of these services. As a hint, the auto-configured docker-compose YAML files are found in `/z/oai-cn5g-fed/docker-compose/` as `cp.yaml` and `upf.yaml` for node-0 and all other nodes, respectively.


If the scripts do not automatically install and start all components so that decentralized nodes are testing each other's UPFs and sharing results with the blockchain, the following steps of manual installtion are slightly oudated but still may come in handy:

First wait until all nodes' startup installation scripts have finished (no more than ~50 minutes). Then, on each of the 4 decentralized nodes (1-4), follow the "Sawtooth PBFT Steps" below. Finally, on all 5 nodes follow the "5G" steps below (note that these instructions vary for node 0 vs nodes 1-4). These two sets of tasks result in the full dNextG network operating correctly (simulated version), and you may want to use `/local/repository/src/persistent-ue.py` to simulate a real user connecting to it.

### Sawtooth PBFT Steps

First, bootstrap with one only node (could be any; I usually pick node-1)
```
sudo pkill -f sawtooth -9; sudo pkill -f settings-tp -9; cd /local/repository/bin && sudo bash install-sawtooth.sh && sudo bash setup-pbft.sh --bootstrap
```

Afterwards, run the following on all others (don't run install-sawtooth.sh again or it will mess up keys)
```
sudo pkill -f sawtooth -9; cd /local/repository/bin/ && sudo bash setup-pbft.sh
```

### 5G Steps

#### 5-node setup (with 4 decentralized nodes): 
node 0 / 10.10.1.1 is the CP (Control Plane) node. Adding more than 4 nodes will not work since OAI doesn't let you use more than 4 DNNs, and requires waiting for that to increase or implementing UPF selection via network slicing.

For initial setup only (NOT restarting things):

1. On node-0, run the following to start the core plane
```
cd /local/repository/bin/ && sudo docker rm -f $(sudo docker ps -a -q); sudo bash gen-configs.sh; cd /z/oai-cn5g-fed/docker-compose/ && sudo docker-compose -f cp.yaml up -d && sudo docker logs -f oai-amf
```
2. On nodes 1-4, start their gNBs - this script now runs the templater script and starts it in a way that it will restart if exit or certain STDERR message appears (so you never have to touch these panes again even if the core crashes):
```
cd /local/repository/bin/ && sudo bash start-gnb.sh
```
3. On nodes 1-4, start their UPFs (and set up other necessary configs):
```
cd /local/repository/bin/ && sudo docker rm -f $(sudo docker ps -a -q) && sudo bash gen-configs.sh; sudo iptables -t nat -A POSTROUTING -o eno1 -j MASQUERADE && cd /z/oai-cn5g-fed/docker-compose/ && sudo docker-compose -f upf.yaml up -d && sudo docker logs -f oai-spgwu
```
4. On nodes 1-4, start the reputation monitor programs which will test other nodes' UPFs and publish transactions to Sawtooth:
```
cd /local/repository/src && sudo python3 monitor.py
```
Or run testupf.sh for a one-time psuedo-UE test (no publishing to Sawtooth):
```
cd /local/repository/bin && sudo bash testupf.sh /local/repository/etc/ue-node2.conf
```

After setup is complete, helpful commands:
- Run `sudo docker rm -f $(sudo docker ps -a -q)` to stop all containers.
- Restart a UPF node: `cd /z/oai-cn5g-fed/docker-compose/ && sudo docker rm -f $(sudo docker ps -a -q); sudo docker-compose -f upf.yaml up -d && sudo docker logs -f oai-spgwu`.
- Restart the node 0's core control plane (all VNFs): `cd /z/oai-cn5g-fed/docker-compose/ && sudo docker rm -f $(sudo docker ps -a -q); sudo docker-compose -f cp.yaml up -d && sudo docker logs -f oai-amf`.

# Known Issues 

- It is unlikely but possible that the AMF and/or SMF can potentially stop processing traffic after 1+ hours. Restarting node 0's core control plane using the above command fixes it. Note that the gNB command used above will automatically handle reconnecting each gNB to the core, but the UPF (spgwu) command may not always automatically reconnect, so restarting each UPF node using the above command is also required.
- The persistent-ue.py 'real UE' simulation OAI UE starting thread may occasionally hang and need restarting (or waiting for a few minutes). Cause not yet identified.
- On very rare occasions, one or more nodes lose Sawtooth ledger consensus (only observed after 800+ blocks). The simplest fix is usually rerunning the "Sawtooth PBFT Steps" which wipes the ledger, though you can attempt to reconnect the out-of-sync node if you desire to maintain the ledger state.
- node-0 (and other nodes) has a small disk space which fills up from logs (check current usage with `df`). If this happens, you can clear disk space with the below command, then restart the control plane VNFs using the 'helpful command' above.

```
sudo docker rm -f $(sudo docker ps -a -q); sudo docker system prune --force
sudo docker volume rm $(sudo docker volume ls -q)
sudo rm -rf /usr/local/share/uhd /tmp/* 
```

"""

tour = IG.Tour()
tour.Description(IG.Tour.MARKDOWN, tourDescription)
tour.Instructions(IG.Tour.TEXT, tourInstructions)
request.addTour(tour)

portal.context.printRequestRSpec()
