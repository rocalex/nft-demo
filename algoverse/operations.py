from typing import Tuple, List

from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient

from .account import Account
from .assets import President
from .contracts import AlgoVerse
from .utils import fullyCompileContract, waitForTransaction, PendingTxnResponse


class BaseApp:
    def __init__(self):
        self.APPROVAL_PROGRAM = b""
        self.CLEAR_STATE_PROGRAM = b""

    def get_contracts(self, client: AlgodClient) -> Tuple[bytes, bytes]:
        app = AlgoVerse()

        if len(self.APPROVAL_PROGRAM) == 0:
            self.APPROVAL_PROGRAM = fullyCompileContract(client, app.approval_program())
            self.CLEAR_STATE_PROGRAM = fullyCompileContract(client, app.clear_program())

        return self.APPROVAL_PROGRAM, self.CLEAR_STATE_PROGRAM

    def create_app(self, client: AlgodClient, creator: Account):
        approval, clear = self.get_contracts(client)

        globalSchema = transaction.StateSchema(num_uints=64,
                                               num_byte_slices=8)  # must be num_units * num_byte_slices = 64
        localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=8)

        txn = transaction.ApplicationCreateTxn(
            sender=creator.getAddress(),
            on_complete=transaction.OnComplete.NoOpOC,
            approval_program=approval,
            clear_program=clear,
            global_schema=globalSchema,
            local_schema=localSchema,
            # accounts=[],  # max number of accounts is 4
            sp=client.suggested_params(),
        )

        signedTxn = txn.sign(creator.getPrivateKey())

        client.send_transaction(signedTxn)

        response = waitForTransaction(client, signedTxn.get_txid())
        assert response.applicationIndex is not None and response.applicationIndex > 0
        return response.applicationIndex

    def close_app(
            self,
            client: AlgodClient,
            appID: int,
            sender: Account
    ):
        deleteTxn = transaction.ApplicationDeleteTxn(
            sender=sender.getAddress(),
            index=appID,
            sp=client.suggested_params()
        )
        signedDeleteTxn = deleteTxn.sign(sender.getPrivateKey())

        client.send_transaction(signedDeleteTxn)

        waitForTransaction(client, signedDeleteTxn.get_txid())

    def fund_algo_to_app(
            self,
            client: AlgodClient,
            funder: Account,
            app_id: int,
    ):
        app_adr = get_application_address(app_id)

        params = client.suggested_params()
        funding_amount = 100_000 + 100_000 + 3 * 1_000
        fund_app_txn = transaction.PaymentTxn(
            sender=funder.getAddress(),
            receiver=app_adr,
            amt=funding_amount,
            sp=params,
        )
        signed_fund_app_txn = fund_app_txn.sign(funder.getPrivateKey())
        client.send_transaction(signed_fund_app_txn)

        waitForTransaction(client, signed_fund_app_txn.get_txid())

    def opt_in_to_asset(
            self,
            client: AlgodClient, asset_id: int, account: Account
    ) -> PendingTxnResponse:
        txn = transaction.AssetOptInTxn(
            sender=account.getAddress(),
            index=asset_id,
            sp=client.suggested_params(),
        )
        signedTxn = txn.sign(account.getPrivateKey())

        client.send_transaction(signedTxn)
        return waitForTransaction(client, signedTxn.get_txid())

    def setup_app(self, client: AlgodClient, sender: Account, app_id: int, asset: President):
        params = client.suggested_params()
        app_args = [b"setup"]
        setup_app_txn = transaction.ApplicationCallTxn(
            sender=sender.getAddress(),
            sp=params,
            index=app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=app_args,
            foreign_assets=[
                asset.base,
                asset.silver,
                asset.gold,
                asset.diamond,
            ]
        )

        signed_setup_app_txn = setup_app_txn.sign(sender.getPrivateKey())

        client.send_transaction(signed_setup_app_txn)

        waitForTransaction(client, signed_setup_app_txn.get_txid())

    def send_asset(self, client: AlgodClient, sender: Account, app_id: int, base_asset_id: int, higher_asset_id: int,
                   amount: int):
        params = client.suggested_params()

        app_args = [
            b"replace",
            amount.to_bytes(8, 'big')
        ]

        call_txn = transaction.ApplicationCallTxn(
            sender=sender.getAddress(),
            index=app_id,
            on_complete=transaction.OnComplete.NoOpOC,
            app_args=app_args,
            foreign_assets=[base_asset_id, higher_asset_id],
            sp=params,
        )

        signed_call_txn = call_txn.sign(sender.getPrivateKey())

        client.send_transaction(signed_call_txn)

        waitForTransaction(client, signed_call_txn.get_txid())

    def destroy_asset(
            self,
            client: AlgodClient,
            sender: Account,
            asset_id: int,
    ):
        params = client.suggested_params()

        txn = transaction.AssetConfigTxn(
            sender=sender.getAddress(),
            index=asset_id,
            strict_empty_address_check=False,
            sp=params
        )
        signedTxn = txn.sign(sender.getPrivateKey())

        client.send_transaction(signedTxn)

        waitForTransaction(client, signedTxn.get_txid())
