from base64 import b64encode, b64decode
import time
import random
import requests
import json
import yaml

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory
from sawtooth_signing import ParseError
from sawtooth_signing.secp256k1 import Secp256k1PrivateKey

from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch

from tp.state import calc_address, _sha512

class D5gException(Exception):
    pass


# communicates with the Sawtooth API in order to get info and send txns. API 
# then forwards request to d5g transaction processor, which eventually gets it
# to validator, and finally to the consensus engine to be published
class D5gBlockchainClient:

    def __init__(self, base_url, keyfile=None):
        self._base_url = base_url
        self.timeout = 15

        try:
            with open(keyfile) as fd:
                private_key_str = fd.read().strip()
        except Exception as e:
            raise D5gException(f"Private key file {keyfile} error: {str(e)}") 
        try:
            private_key = Secp256k1PrivateKey.from_hex(private_key_str)
        except ParseError as e:
            raise D5gException(f"Private key load error: {e}")

        self._signer = CryptoFactory(create_context('secp256k1')) \
            .new_signer(private_key)

    def _send_request(self, suffix, data=None, content_type=None):
        if self._base_url.startswith("http://"):
            url = "{}/{}".format(self._base_url, suffix)
        else:
            url = "http://{}/{}".format(self._base_url, suffix)
        headers = {}
        if content_type is not None:
            headers['Content-Type'] = content_type
        try:
            if data is not None:
                result = requests.post(url, headers=headers, data=data, timeout=self.timeout)
            else:
                result = requests.get(url, headers=headers, timeout=self.timeout)

            if result.status_code == 404:
                raise D5gException("API responded with 404 ")
            if not result.ok:
                raise D5gException(f"API responded with error {result.status_code}: {result.reason}")
        except requests.ConnectionError as e:
            raise D5gException( f"API connection error to url {url}: {str(e)}") from e
        except BaseException as e:
            raise D5gException(e) from e

        return result.text

    # todo rename to state of node, not just one txn
    def get_txn(self, pubkey, auth_user=None, auth_password=None):
        address = calc_address(pubkey)
        result = self._send_request(
            f"state/{address}")
        try:
            return b64decode(yaml.safe_load(result)["data"])

        except BaseException:
            return None

    # from xo tp example but unused currently
    def _get_status(self, batch_id, wait, auth_user=None, auth_password=None):
        try:
            result = self._send_request(
                'batch_statuses?id={}&wait={}'.format(batch_id, wait),
                auth_user=auth_user,
                auth_password=auth_password)
            return yaml.safe_load(result)['data'][0]['status']
        except BaseException as err:
            raise D5gException(err) from err

    # derived from xo tp 
    def send_transaction(self, payload, wait=None, auth_user=None, auth_password=None):
        # Serialization is just a delimited utf-8 encoded string
        address = calc_address(self._signer.get_public_key().as_hex())
        payload = json.dumps(payload).encode("utf-8")

        header = TransactionHeader(
            signer_public_key=self._signer.get_public_key().as_hex(),
            family_name="d5g",
            family_version="1.0",
            inputs=[address],
            outputs=[address],
            dependencies=[],
            payload_sha512=_sha512(payload),
            batcher_public_key=self._signer.get_public_key().as_hex(),
            nonce=hex(random.randint(0, 2**64))
        ).SerializeToString()

        signature = self._signer.sign(header)

        transaction = Transaction(
            header=header,
            payload=payload,
            header_signature=signature
        )

        batch_list = self._create_batch_list([transaction])
        batch_id = batch_list.batches[0].header_signature
        
        if wait and wait > 0:
            wait_time = 0
            start_time = time.time()
            response = self._send_request(
                "batches", batch_list.SerializeToString(),
                'application/octet-stream',
                auth_user=auth_user,
                auth_password=auth_password)
            while wait_time < wait:
                status = self._get_status(
                    batch_id,
                    wait - int(wait_time),
                    auth_user=auth_user,
                    auth_password=auth_password)
                wait_time = time.time() - start_time

                if status != 'PENDING':
                    return response

            return response

        return self._send_request(
            "batches", batch_list.SerializeToString(),
            'application/octet-stream')

    def _create_batch_list(self, transactions):
        transaction_signatures = [t.header_signature for t in transactions]

        header = BatchHeader(
            signer_public_key=self._signer.get_public_key().as_hex(),
            transaction_ids=transaction_signatures
        ).SerializeToString()

        signature = self._signer.sign(header)

        batch = Batch(
            header=header,
            transactions=transactions,
            header_signature=signature, trace=True)
        return BatchList(batches=[batch])