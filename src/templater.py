import subprocess
import sys

powdernet_subnet = "10.10.1.0/24"

def get_node_number():
    hostname = subprocess.getoutput("hostname -s")
    return int(hostname[-1])

def get_cp_interface():
    return subprocess.getoutput("ip route list " + powdernet_subnet + " | awk '{print $3}'")


def get_cp_ip():
    return "10.10.1.1"

def get_upf_ip():
    return subprocess.getoutput("ip route list " + powdernet_subnet + " | awk '{print $9}'")

def get_upf_sst():
    return get_node_number()    
def get_upf_sd():
    return get_node_number()    
def get_upf_dnn():
    letter_byte_offset = 96
    node_letter = chr(get_node_number() + letter_byte_offset)
    # i.e. node1 -> adnn
    return node_letter + "dnn"


# substitute template string with another
def sub(var, text, replace_fn):
    templvar = "{{" + var + "}}"
    replacement = str(replace_fn())
    return text.replace(templvar, replacement)


if __name__ == "__main__":
    args = sys.argv
    print(args)
    if len(args) != 2 + 1:
        print('Usage: <template_file> <output_file>')
        exit(1)

    upf_tmpl = args[1]
    newfile = args[2]

    newtext = None
    with open(upf_tmpl) as template:
        text = template.read()
        text = sub("cp-network-interface", text, get_cp_interface)
        text = sub("cp-ip-address", text, get_cp_ip)
        text = sub("upf-ip-address", text, get_upf_ip)
        text = sub("upf-sst", text, get_upf_sst)
        text = sub("upf-sd", text, get_upf_sd)
        text = sub("upf-dnn", text, get_upf_dnn)
        newtext = text

    with open(newfile, 'w') as f:
        f.write(newtext)
