import logging
from tp.state import D5G_NAMESPACE, D5gNodeState
from tp.d5g_payload import D5gUpPayload
from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InternalError
from templater import get_node_number, get_num_decentralized_nodes

# TODO use for handling errors when necessary 
LOGGER = logging.getLogger(__name__)

class D5gTransactionHandler(TransactionHandler):
    # pylint: disable=invalid-overridden-method
    @property
    def family_name(self):
        return 'd5g'

    @property
    def family_versions(self):
        return ['1.0']

    @property
    def namespaces(self):
        return [D5G_NAMESPACE]
    
    def apply(self, transaction, context):
        # signer = header.signer_public_key
        header = transaction.header

        payload = D5gUpPayload.from_bytes(transaction.payload)
        num_nodes = get_num_decentralized_nodes()
        # instead of THIS node's number, need to use node number from the payload
        state = D5gNodeState(context, transaction.header.batcher_public_key, num_nodes, payload.nid)
        state.update_reputation_state(payload)
        #state.store_data(transaction.header.batcher_public_key, payload.epic, payload.as_bytes)
