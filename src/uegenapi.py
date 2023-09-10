import subprocess
import random
from flask import Flask

app = Flask(__name__)

@app.route("/gen-ue/<nodenum>", methods=['GET'])
def generate_ue(nodenum):
    nonce = random.randint(1000000, 9999999)
    uefile = f"/tmp/testue-{nonce}.conf"
    print(subprocess.getoutput(f"sudo bash /local/repository/bin/gen_new_ue.sh {uefile} {nodenum}"))
    with open(uefile, 'r') as f:
        return f.read()

@app.route("/remove-ue/<imsi>", methods=['GET'])
def remove_ue(imsi):
    return subprocess.getoutput(f"sudo bash /local/repository/bin/remove_ue.sh {imsi}")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=18693, debug=True)
