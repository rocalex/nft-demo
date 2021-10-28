from typing import Tuple

from algosdk.future import transaction
from algosdk.logic import get_application_address
from algosdk.v2client.algod import AlgodClient

from .account import Account
from .contracts import AlgoVerse
from .utils import fullyCompileContract, waitForTransaction, PendingTxnResponse

APPROVAL_PROGRAM = b""
CLEAR_STATE_PROGRAM = b""


def getContracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    """Get the compiled TEAL contracts for the auction.

    Args:
        client: An algod client that has the ability to compile TEAL programs.

    Returns:
        A tuple of 2 byte strings. The first is the approval program, and the
        second is the clear state program.
    """
    global APPROVAL_PROGRAM
    global CLEAR_STATE_PROGRAM

    app = AlgoVerse()

    if len(APPROVAL_PROGRAM) == 0:
        APPROVAL_PROGRAM = fullyCompileContract(client, app.approval_program())
        CLEAR_STATE_PROGRAM = fullyCompileContract(client, app.clear_program())

    return APPROVAL_PROGRAM, CLEAR_STATE_PROGRAM


def createAlgoVerseApp(client: AlgodClient, creator: Account):
    approval, clear = getContracts(client)

    globalSchema = transaction.StateSchema(num_uints=32, num_byte_slices=2)  # must be num_units * num_byte_slices = 64
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


def closeAlgoVerseApp(
        client: AlgodClient,
        appID: int,
        sender: Account
):
    """
    Close application

    Args:
        client:
        appID:
        sender:
    """
    deleteTxn = transaction.ApplicationDeleteTxn(
        sender=sender.getAddress(),
        index=appID,
        sp=client.suggested_params()
    )
    signedDeleteTxn = deleteTxn.sign(sender.getPrivateKey())

    client.send_transaction(signedDeleteTxn)

    waitForTransaction(client, signedDeleteTxn.get_txid())


def fundAlgoToApp(
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


def optInToAsset(
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


def setupAlgoVerseApp(client: AlgodClient, sender: Account, app_id: int, asset_id: int):
    params = client.suggested_params()

    setup_app_txn = transaction.ApplicationCallTxn(
        sender=sender.getAddress(),
        sp=params,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[
            b"setup"
        ],
        foreign_assets=[asset_id]
    )

    signed_setup_app_txn = setup_app_txn.sign(sender.getPrivateKey())

    client.send_transaction(signed_setup_app_txn)

    waitForTransaction(client, signed_setup_app_txn.get_txid())


def transferAssetToApp(client: AlgodClient, sender: Account, app_id: int, asset_id: int, amount: int):
    app_adr = get_application_address(app_id)
    params = client.suggested_params()

    fund_asset_txn = transaction.AssetTransferTxn(
        sender=sender.getAddress(),
        receiver=app_adr,
        index=asset_id,
        amt=amount,
        sp=params,
    )

    signed_fund_asset_txn = fund_asset_txn.sign(sender.getPrivateKey())

    client.send_transaction(signed_fund_asset_txn)

    waitForTransaction(client, signed_fund_asset_txn.get_txid())


