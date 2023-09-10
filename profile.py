#!/usr/bin/python

import os

import geni.portal as portal
import geni.urn as URN
import geni.rspec.pg as rspec
import geni.rspec.emulab.pnext as PN
import geni.rspec.igext as IG
import geni.rspec.emulab.spectrum as spectrum

scripts_dir = "/local/repository/bin/"

# derived from https://gitlab.flux.utah.edu/dmaas/oai-indoor-ota.git
BIN_PATH = "/local/repository/bin"
ETC_PATH = "/local/repository/etc"
D5G_IMG = "urn:publicid:IDN+emulab.net+image+PowderSandbox:d5g.node"
LOWLAT_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:U18LL-SRSLTE"
UBUNTU_IMG = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU18-64-STD"
COTS_UE_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:cots-base-image"
COMP_MANAGER_ID = "urn:publicid:IDN+emulab.net+authority+cm"
# old hash from branch bandwidth-testing-abs-sr-bsr-multiple_ue
#TODO: check if merged to develop or develop now supports multiple UEs
DEFAULT_NR_RAN_HASH = "509168255153690397626d85cdd4c4aec0859620" # 2022.wk26
DEFAULT_NR_CN_HASH = "v1.2.1"
OAI_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-oai.sh")








def invoke_script_str(filename):
    # populate script config before running scripts (replace '?'s)
    #populate_config = "sed -i 's/NUM_UE_=?/NUM_UE_=" + str(params.uenum) + "/' " + GLOBALS.SCRIPT_DIR+GLOBALS.SCRIPT_CONFIG
    #populate_config2 = "sed -i 's/UERANSIM_BRANCHTAG_=?/UERANSIM_BRANCHTAG_=" + str(params.ueransim_branchtag) + "/' " + GLOBALS.SCRIPT_DIR+GLOBALS.SCRIPT_CONFIG
    # also redirect all output to /script_output
    run_script = "sudo bash " + scripts_dir + filename + " &> ~/" + filename + "_output"
    #return populate_config + " && " + populate_config2 + " && " +  run_script
    return run_script

pc = portal.context




# Parameters

node_types = [
    ("d430", "Emulab, d430"),
    ("d740", "Emulab, d740"),
]

pc.defineParameter("phystype",  "Optional physical node type",
                   portal.ParameterType.STRING, "",
                   longDescription="Specify a physical node type (d430,d740,d840, NOT d820) " +
                   "instead of letting the resource mapper choose for you.")
pc.defineParameter(
		"nodeCount","Number of Nodes",
    portal.ParameterType.INTEGER,5,
    longDescription="Number of nodes to spin up, all with the same installations.")

pc.defineParameter(
    name="sdr_nodetype",
    description="Type of compute node paired with the SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[1],
    legalValues=node_types
)

pc.defineParameter(
    name="cn_nodetype",
    description="Type of compute node to use for CN node (if included). Overrides optional physical node type.",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[0],
    legalValues=node_types
)

# pc.defineParameter(
#     name="oai_ran_commit_hash",
#     description="Commit hash for OAI RAN",
#     typ=portal.ParameterType.STRING,
#     defaultValue="",
#     advanced=True
# )
# 
# pc.defineParameter(
#     name="oai_cn_commit_hash",
#     description="Commit hash for OAI (5G)CN",
#     typ=portal.ParameterType.STRING,
#     defaultValue="",
#     advanced=True
# )

pc.defineParameter(
    name="sdr_compute_image",
    description="Image to use for compute connected to SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

indoor_ota_x310s = [
    ("ota-x310-1",
     "USRP X310 #1"),
    ("ota-x310-2",
     "USRP X310 #2"),
    ("ota-x310-3",
     "USRP X310 #3"),
    ("ota-x310-4",
     "USRP X310 #4"),
]
pc.defineParameter(
    name="x310_radio",
    description="X310 Radio (for OAI gNodeB)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[0],
    legalValues=indoor_ota_x310s
)

portal.context.defineStructParameter(
    "freq_ranges", "Frequency Ranges To Transmit In",
    defaultValue=[{"freq_min": 3550.0, "freq_max": 3600.0}],
    multiValue=True,
    min=0,
    multiValueTitle="Frequency ranges to be used for transmission.",
    members=[
        portal.Parameter(
            "freq_min",
            "Frequency Range Min",
            portal.ParameterType.BANDWIDTH,
            3550.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
        portal.Parameter(
            "freq_max",
            "Frequency Range Max",
            portal.ParameterType.BANDWIDTH,
            3600.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
    ]
)


params = pc.bindParameters()
pc.verifyParameters()
request = pc.makeRequestRSpec()
link = request.Link("link")
link.bandwidth = 10*1000*1000

def x310_node_pair(idx, x310_radio):
    role = "nodeb"
    #node = request.RawPC("{}-gnb-comp".format(x310_radio))
    node = request.RawPC("node-1")
    node.component_manager_id = COMP_MANAGER_ID
    node.hardware_type = params.sdr_nodetype

    if params.sdr_compute_image:
        node.disk_image = params.sdr_compute_image
    else:
        node.disk_image = LOWLAT_IMG

    node_radio_if = node.addInterface("usrp_if")
    # node_radio_if.addAddress(rspec.IPv4Address("192.168.40.1",
#                                               "255.255.255.0"))

    radio_link = request.Link("radio-link-{}".format(idx))
    radio_link.bandwidth = 10*1000*1000
    radio_link.addInterface(node_radio_if)

    radio = request.RawPC("{}-gnb-sdr".format(x310_radio))
    radio.component_id = x310_radio
    radio.component_manager_id = COMP_MANAGER_ID
    radio_link.addNode(radio)

    nodeb_cn_if = node.addInterface("nodeb-cn-if")
    # nodeb_cn_if.addAddress(rspec.IPv4Address("192.168.1.{}".format(idx + 1), "255.255.255.0"))
    link.addInterface(nodeb_cn_if)
    bs = node.Blockstore("bs{}".format(i), "/z")
    bs.size = "20GB"

    cmd = "{} '{}' {}".format(OAI_DEPLOY_SCRIPT, DEFAULT_NR_RAN_HASH, role)
    node.addService(rspec.Execute(shell="bash", command=cmd))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))
    node.addService(rspec.Execute(shell="bash", command=invoke_script_str("install-5g.sh")))
    node.addService(rspec.Execute(shell="bash", command=invoke_script_str("install-sawtooth.sh")))

def b210_nuc_pair(b210_node):
    node = request.RawPC("{}-cots-ue".format(b210_node))
    node.component_manager_id = COMP_MANAGER_ID
    node.component_id = b210_node
    node.disk_image = COTS_UE_IMG
    node.addService(rspec.Execute(shell="bash", command="/local/repository/bin/module-off.sh"))



# node definitions

for i in range(0,params.nodeCount):
    # single real gNB
    if i == 1:
        x310_node_pair(1, params.x310_radio)
        continue
    nodename = "node-%d" % (i,)
    node = request.RawPC(nodename)
    node.component_manager_id = COMP_MANAGER_ID
    node.disk_image = D5G_IMG
    node.hardware_type = "d430" if params.phystype == "" else params.phystype
    # cn node may have different type
    if i == 0 and params.cn_nodetype != "":
        node.hardware_type = params.cn_nodetype
    node.addService(rspec.Execute(shell="bash", command=invoke_script_str("install-5g.sh")))
    node.addService(rspec.Execute(shell="bash", command=invoke_script_str("install-sawtooth.sh")))
    bs = node.Blockstore("bs{}".format(i), "/z")
    bs.size = "20GB"
    link.addNode(node)



# require all indoor OTA nucs to prevent interference
for b210_node in ["ota-nuc1", "ota-nuc2", "ota-nuc3", "ota-nuc4"]:
    b210_nuc_pair(b210_node)

for frange in params.freq_ranges:
    request.requestSpectrum(frange.freq_min, frange.freq_max, 0)


# README info

tourDescription = """
# dNextG (outdated branch)

This should only be used if attempting to run dNextG with COTS UEs, and must be manually set up (which will probably be difficult).

### D5G - Decentralized 5G

This profile instantiates an experiment that runs a simulated 5G RAN and Core 
network on Docker, along with a Hyperledger Sawtooth validator node and an Orchestrator
program that sits between them. It will eventually include several nodes.
"""

tourInstructions = """
Start the Validator (must start many background processes)

sudo -u sawtooth sawtooth-validator -vv &
sudo -u sawtooth settings-tp -v &
sudo -u sawtooth devmode-engine-rust -vv --connect tcp://localhost:5050 &
sudo -u sawtooth intkey-tp-python -v &
sudo -u sawtooth sawtooth-rest-api -v

To delete the blockchain data, remove all files from /var/lib/sawtooth.
To delete the Sawtooth logs, remove all files from /var/log/sawtooth/.
To delete the Sawtooth keys, remove the key files /etc/sawtooth/keys/validator.\* and /home/yourname/.sawtooth/keys/yourname.\*.

More: https://sawtooth.hyperledger.org/docs/core/nightly/1-2/app_developers_guide/ubuntu.html
"""

tour = IG.Tour()
tour.Description(IG.Tour.MARKDOWN, tourDescription)
tour.Instructions(IG.Tour.TEXT, tourInstructions)
request.addTour(tour)

portal.context.printRequestRSpec()
