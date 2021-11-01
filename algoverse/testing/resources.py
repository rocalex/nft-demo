from random import randint
from typing import List

from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient

from ..account import Account
from ..utils import waitForTransaction

FUNDING_AMOUNT = 100_000

accountList: List[Account] = []


def createNFT(client: AlgodClient, creator: Account) -> int:
    randomNumber = randint(0, 999)
    # this random note reduces the likelihood of this transaction looking like a duplicate
    randomNote = bytes(randint(0, 255) for _ in range(20))

    txn = transaction.AssetCreateTxn(
        sender=creator.getAddress(),
        total=1,  # NFTs have totalIssuance of exactly 1
        decimals=0,  # NFTs have decimals of exactly 0
        default_frozen=False,
        manager=creator.getAddress(),
        reserve=creator.getAddress(),
        freeze=creator.getAddress(),
        clawback=creator.getAddress(),
        unit_name=f"D{randomNumber}",
        asset_name=f"ALGOVERSE NFT {randomNumber}",
        url=f"https://dummy.asset/{randomNumber}",
        note=randomNote,
        sp=client.suggested_params(),
    )
    signedTxn = txn.sign(creator.getPrivateKey())

    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    assert response.assetIndex is not None and response.assetIndex > 0
    return response.assetIndex


def createToken(client: AlgodClient, creator: Account, amount: int, clawback_address: str) -> int:
    randomNumber = randint(1, 45)

    txn = transaction.AssetConfigTxn(
        sender=creator.getAddress(),
        sp=client.suggested_params(),
        total=amount,  # Fungible tokens have totalIssuance greater than 1
        decimals=0,  # Fungible tokens typically have decimals greater than 0
        default_frozen=False,
        unit_name="President",
        asset_name=f"President {randomNumber}",
        manager=creator.getAddress(),
        reserve=creator.getAddress(),
        freeze=creator.getAddress(),
        clawback=clawback_address
    )

    signedTxn = txn.sign(creator.getPrivateKey())

    client.send_transaction(signedTxn)

    response = waitForTransaction(client, txn.get_txid())

    assert response.assetIndex is not None and response.assetIndex > 0
    return response.assetIndex
