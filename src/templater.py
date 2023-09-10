import subprocess
import sys

powdernet_subnet = "10.10.1.0/24"
decentralized_node_count = 0

# with 3 places for gnb id.
def get_node_number_hex():
    nid = get_node_number()
    if nid > 4095:
        raise Exception("d5g only supports up to 4095 nodes because of gNB ID fff value")
    hexstr = f'{nid:03x}'
    return hexstr

def get_node_number():
    hostname = subprocess.getoutput("hostname -s")
    return int(hostname.split('-')[1])

def get_cp_interface():
    return subprocess.getoutput("ip route list " + powdernet_subnet + " | awk '{print $3}'")


def get_cp_ip():
    return "10.10.1.1"

def get_upf_ip():
    return subprocess.getoutput("ip route list " + powdernet_subnet + " | awk '{print $9}'")

def get_upf_dnn():
    return "dnn" + str(get_node_number())

def get_num_decentralized_nodes():
    with open('/tmp/num_decentralized_nodes', 'r') as f:
        return int(f.readlines()[0])


def generate_validator_conf_peers():
    global decentralized_node_count
    itemstr = '['
    this_nid = get_node_number()
    for nip in range(2, decentralized_node_count+2):
        if this_nid + 1 == nip:
            pass #continue  going to include as possibly should be included?
        # IPV6_PREFIX might be required but isn't used, so ignore
        itemstr += f'"tcp://10.10.1.{nip}:8800", '
    return itemstr[:-2] + ']'  # remove final comma and space and add a closing bracket

def generate_smf_conf_dnn_list_items():
    global decentralized_node_count
    itemstr = ''
    for nid in range(1, decentralized_node_count+1):
        # IPV6_PREFIX might be required but isn't used, so ignore
        itemstr += f'{{DNN_NI = "dnn{nid}"; PDU_SESSION_TYPE = "IPv4"; IPV4_RANGE = "12.1.{nid}.2 - 12.1.{nid}.128"; IPV6_PREFIX = "3001:1:2::/64"}},\n      '
    return itemstr[:-8]  # remove final newline, comma, spaces


# substitute template string with another
def sub(var, text, replace_fn):
    templvar = "{{" + var + "}}"
    replacement = str(replace_fn())
    return text.replace(templvar, replacement)


if __name__ == "__main__":
    args = sys.argv
    print(args)
    if len(args) != 3 + 1:
        print('Usage: <template_file> <output_file> <decentralized node count>')
        exit(1)

    upf_tmpl = args[1]
    newfile = args[2]
    decentralized_node_count = int(args[3])

    newtext = None
    with open(upf_tmpl) as template:
        text = template.read()
        text = sub("cp-network-interface", text, get_cp_interface)
        text = sub("cp-ip-address", text, get_cp_ip)
        text = sub("upf-ip-address", text, get_upf_ip)
        text = sub("upf-sst", text, get_node_number)
        text = sub("upf-sd", text, get_node_number)
        text = sub("nid", text, get_node_number)
        text = sub("nid-hex", text, get_node_number_hex)
        text = sub("decentralized-node-number", text, get_node_number)
        text = sub("upf-dnn", text, get_upf_dnn)
        text = sub("smf-conf-dnn-item-list", text, generate_smf_conf_dnn_list_items)
        text = sub("validator-conf-peers", text, generate_validator_conf_peers)
        newtext = text

    with open(newfile, 'w') as f:
        f.write(newtext)
