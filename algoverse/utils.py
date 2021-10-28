import os
from base64 import b64decode
from typing import Dict, Union, List, Any, Optional

from algosdk import encoding
from algosdk.v2client.algod import AlgodClient
from pyteal import compileTeal, Expr, Mode

from .account import Account


def getAlgodClient() -> AlgodClient:
    algod_address = os.environ.get('ALGOD_ADDRESS')
    algod_token = os.environ.get('ALGOD_TOKEN')
    headers = {
        'X-API-Key': algod_token
    }
    return AlgodClient(algod_token, algod_address, headers)


class PendingTxnResponse:
    def __init__(self, response: Dict[str, Any]) -> None:
        self.poolError: str = response["pool-error"]
        self.txn: Dict[str, Any] = response["txn"]

        self.applicationIndex: Optional[int] = response.get("application-index")
        self.assetIndex: Optional[int] = response.get("asset-index")
        self.closeRewards: Optional[int] = response.get("close-rewards")
        self.closingAmount: Optional[int] = response.get("closing-amount")
        self.confirmedRound: Optional[int] = response.get("confirmed-round")
        self.globalStateDelta: Optional[Any] = response.get("global-state-delta")
        self.localStateDelta: Optional[Any] = response.get("local-state-delta")
        self.receiverRewards: Optional[int] = response.get("receiver-rewards")
        self.senderRewards: Optional[int] = response.get("sender-rewards")

        self.innerTxns: List[Any] = response.get("inner-txns", [])
        self.logs: List[bytes] = [b64decode(l) for l in response.get("logs", [])]


def waitForTransaction(
        client: AlgodClient, txID: str
) -> PendingTxnResponse:
    lastStatus = client.status()
    last_round = lastStatus.get("last-round")
    pending_txn = client.pending_transaction_info(txID)
    while not (pending_txn.get("confirmed-round") and pending_txn.get("confirmed-round") > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        pending_txn = client.pending_transaction_info(txID)
    print(
        "Transaction {} confirmed in round {}.".format(
            txID, pending_txn.get("confirmed-round")
        )
    )
    return PendingTxnResponse(pending_txn)


def fullyCompileContract(client: AlgodClient, contract: Expr) -> bytes:
    teal = compileTeal(contract, mode=Mode.Application, version=5)
    response = client.compile(teal)
    return b64decode(response["result"])


def decodeState(stateArray: List[Any]) -> Dict[bytes, Union[int, bytes]]:
    state: Dict[bytes, Union[int, bytes]] = dict()

    for pair in stateArray:
        key = b64decode(pair["key"])

        value = pair["value"]
        valueType = value["type"]

        if valueType == 2:
            # value is uint64
            value = value.get("uint", 0)
        elif valueType == 1:
            # value is byte array
            value = b64decode(value.get("bytes", ""))
        else:
            raise Exception(f"Unexpected state type: {valueType}")

        state[key] = value

    return state


def getAppGlobalState(
        client: AlgodClient, appID: int
) -> Dict[bytes, Union[int, bytes]]:
    appInfo = client.application_info(appID)
    return decodeState(appInfo["params"]["global-state"])


def getAppLocalState(
        client: AlgodClient, appID: int, sender: Account
) -> Dict[bytes, Union[int, bytes]]:
    accountInfo = client.account_info(sender.getAddress())
    for local_state in accountInfo["apps-local-state"]:
        if local_state["id"] == appID:
            if "key-value" not in local_state:
                return {}

            return decodeState(local_state["key-value"])
    return {}


def getAppAddress(appID: int) -> str:
    toHash = b"appID" + appID.to_bytes(8, "big")
    return encoding.encode_address(encoding.checksum(toHash))


def getBalances(client: AlgodClient, account: str) -> Dict[int, int]:
    balances: Dict[int, int] = dict()

    accountInfo = client.account_info(account)

    # set key 0 to Algo balance
    balances[0] = accountInfo["amount"]

    assets: List[Dict[str, Any]] = accountInfo.get("assets", [])
    for assetHolding in assets:
        assetID = assetHolding["asset-id"]
        amount = assetHolding["amount"]
        balances[assetID] = amount

    return balances
