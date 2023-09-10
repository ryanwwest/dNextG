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

        self.as_bytes = payload

    @staticmethod
    def from_bytes(payload):
        # TODO 
        return D5gUpPayload(payload=payload)
