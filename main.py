import os
import traceback

import dotenv
from algosdk.error import AlgodHTTPError

from algoverse.account import Account
from algoverse.operations import createAlgoVerseApp, fundAlgoToApp, setupAlgoVerseApp, transferAssetToApp
from algoverse.testing.resources import createToken
from algoverse.utils import getAlgodClient, getAppAddress


def main():
    client = getAlgodClient()
    creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))
    print("=========================================")
    print("Deploying the smart contract....")
    app_id = createAlgoVerseApp(
        client=client,
        creator=creator
    )
    print("App ID: ", app_id)
    print("App Address:", getAppAddress(app_id))  # max apps per acct is 10

    for _ in range(45):
        try:
            print("=========================================")
            print("Alice is generating an example token....")
            token_id = createToken(client, creator)
            print("The Token ID is:", token_id)

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
                amount=100
            )
        except AlgodHTTPError:
            traceback.print_exc()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    main()
