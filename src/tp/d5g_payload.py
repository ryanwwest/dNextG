from sawtooth_sdk.processor.exceptions import InvalidTransaction
import json

class D5gUpPayload:

    def __init__(self, payload):
        try:
            j = json.loads(payload.decode()) # this should create a json object
        except ValueError as e:
            raise InvalidTransaction("Invalid payload serialization") from e

        if not 'tested_nodes' in j or len(j['tested_nodes']) == 0:
            raise InvalidTransaction('Missing tested_nodes')
        self.tested_nodes = j['tested_nodes']

        if not 'timestamp' in j:
            raise InvalidTransaction('Missing timestamp')
        self.timestamp = j['timestamp']

        # the public key that signed the txn, not this, should be used to verify who 
        # actually sent the payload. This isn't verified.
        if not 'nid' in j:
            raise InvalidTransaction('Missing nid')
        self.nid = j['nid']

        # needed to verify the random seed used for test selection (and tracking how 
        # often nodes report)
        if not 'seedblock' in j:
            raise InvalidTransaction('Missing seedblock')
        self.seedblock = j['seedblock']

        self.as_bytes = payload

    @staticmethod
    def from_bytes(payload):
        # TODO 
        return D5gUpPayload(payload=payload)
