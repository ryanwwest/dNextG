import hashlib
from sawtooth_sdk.processor.exceptions import InternalError
from tp.d5g_payload import D5gUpPayload
import json

def _sha512(data):
    return hashlib.sha512(data).hexdigest()

def _get_d5g_prefix():
    return _sha512('d5g'.encode('utf-8'))[0:6]

# 70 hex char length, or 35 bytes
# only use pubkey and store the last X (e.g. 50) reputation results
#     as current address state
def calc_address(pubkey):
    d5g_part = _get_d5g_prefix()
    # todo make this into class in case json changes
    pubkey_part = _sha512(pubkey.encode('utf-8'))[0:64]
    #epic_part = f"{epic:#0{32}}"
    return d5g_part + pubkey_part #+ epic_part


D5G_NAMESPACE = hashlib.sha512('d5g'.encode("utf-8")).hexdigest()[0:6]

val_if_self_reference = -9 # not using because non-deterministic

class UpNodeReputationState:
    def __init__(self, cur_node_num=None, num_nodes=None, prev_state=None):
        if cur_node_num is None and prev_state is None:
            raise Exception("Must provide current node's number of prev state")
        if num_nodes is not None:
            # default to 5, can go to 0 or 10 depending on behavior
            # node's own reputation will be ignored by UE and is set to -9
            self.reputations = {str(x): 5 for x in range(1,num_nodes+1)}
            # todo this should ideally have its own field, not share the dict with rep vals
            self.reputations['nid_reporter'] = str(cur_node_num)
            # self.reputations[str(cur_node_num)] = val_if_self_reference
        elif prev_state is not None:
            self.reputations = prev_state
        else:
            raise Exception("Need to supply num_nodes or prev_state")


# Actually gets and sets data on the blockchain via the context class.
class D5gNodeState:
    TIMEOUT = 3

    # loads current state from node's own public key / address on blockchain.
    def __init__(self, context, pubkey, num_nodes, cur_node_num):
        self.context = context
        self.pubkey = pubkey
        self.max = 10
        self.min = 0
        self.delta = 1  # how much does a new reputation txn affect state?
        self.rep_state_cache = self.load_data()
        # create if doesn't yet exist. could throw exception though?
        if self.rep_state_cache is None:
            self.rep_state_cache = UpNodeReputationState(cur_node_num, 
                num_nodes=num_nodes)
            self.store_data(self.rep_state_cache)

    # a node's transaction payload will update the state stored at its
    # address by incrementing or decrementing the reputation of its peer
    # nodes.
    def update_reputation_state(self, payload: D5gUpPayload):
        # TODO if payload timestamp is older than the existing timestamps in
        # any other transaction that belongs to this address/node, reject it
        if self.rep_state_cache is None:
            self.load_data(self.pubkey)
        if int(self.rep_state_cache.reputations['nid_reporter']) != int(payload.nid):
            raise Exception(f"Payload nid {payload.nid} does not match state reputation reporter nid {self.rep_state_cache.reputations['nid_reporter']}.")
        for nid, connection_verified in payload.tested_nodes.items():
            # don't change value of node's own reputation - this gets ignored
            if self.rep_state_cache.reputations[nid] == val_if_self_reference:
                continue
            # shouldn't need to check if node id equals self since this 
            # isn't reported
            change = self.delta if connection_verified else -self.delta
            self.rep_state_cache.reputations[nid] += change
            if self.rep_state_cache.reputations[nid] > self.max:
                self.rep_state_cache.reputations[nid] = self.max
            if self.rep_state_cache.reputations[nid] < self.min:
                self.rep_state_cache.reputations[nid] = self.min
        self.store_data(self.rep_state_cache)


    # could optionally add cache like xo
    def store_data(self, data):
        address = calc_address(self.pubkey)
        self.context.set_state(
            {address: self._serialize(data)},
            timeout=self.TIMEOUT)

    def delete_data(self):
        address = calc_address(self.pubkey)
        self.context.delete_state(
            [address],
            timeout=self.TIMEOUT)

    def load_data(self):
        address = calc_address(self.pubkey)
        state_entries = self.context.get_state(
            [address],
            timeout=self.TIMEOUT)
        data = None
        if state_entries:
            data = self._deserialize(data=state_entries[0].data)
        return data

    def _deserialize(self, data):
        return UpNodeReputationState(prev_state=json.loads(data.decode("utf-8")))

    def _serialize(self, data: UpNodeReputationState):
        return json.dumps(data.reputations, sort_keys = True).encode('utf-8')
