import os
import traceback

import dotenv
from algosdk.error import AlgodHTTPError

from algoverse.account import Account
from algoverse.operations import transferAssetToApp, setupAlgoVerseApp, fundAlgoToApp
from algoverse.utils import getAlgodClient


def main():
    creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))

    client = getAlgodClient()
    app_id = 170
    amount = 100

    for i in range(45):
        token_id = 108 + i
        try:
            print("=========================================")
            print("Funding Algo to the smart contract....")
            fundAlgoToApp(
                client=client,
                funder=creator,
                app_id=app_id,
            )

            print("=========================================")
            print("Setting up the app....")
            setupAlgoVerseApp(client, creator, app_id, token_id)

            print("=========================================")
            print("Transferring token to app....")
            transferAssetToApp(
                client=client,
                app_id=app_id,
                sender=creator,
                asset_id=token_id,
                amount=amount
            )
        except AlgodHTTPError:
            traceback.print_exc()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    main()
