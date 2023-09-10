import subprocess
import os
import shlex
import signal

bad_logs = [
    b"No AMF is associated to the gNB", # when core cp vnfs restart 
    b"Failed to find SCTP description for assoc_id",
    #b"Detected UL Failure on PUSCH after",
    b"Received NGAP_DEREGISTERED_GNB_IND"
    #b"RU 0 rf device ready"  # for debugging only
]

cmd = "sudo RFSIMULATOR=server /z/openairinterface5g/cmake_targets/ran_build/build/nr-softmodem --rfsim --sa -O /local/repository/etc/gnb.conf"

print_all_output = True

while True:
    restart = False
    while not restart:
        print('starting gnb...')
        no_output_count = 0
        proc = subprocess.Popen(shlex.split(cmd),stdout=subprocess.PIPE, shell=False, preexec_fn=os.setsid)
        for line in iter(proc.stdout.readline,''):
            l = line.strip()
            if print_all_output and l is not None and len(l) > 0:
                print(line)
            for bl in bad_logs:
                if bl in l:
                    print(f"DETECTED BAD LOG PART ({bl})")
                    print(f"RESTARTING GNB...")
                    restart = True
                    break
            if l is None or len(l) == 0:
                no_output_count += 1
                print("didn't detect output")
            else:
                no_output_count = 0
            if no_output_count == 20:  # meant to catch bug if for some reason process dies
                restart = True
            if restart:
                proc.stdout.close()
                os.killpg(os.getpgid(proc.pid), signal.SIGHUP)
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                print('killed old gnb process')
                break
