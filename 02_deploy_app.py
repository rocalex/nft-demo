import os
import traceback

import dotenv
from algosdk.error import AlgodHTTPError

from algoverse.account import Account
from algoverse.operations import createAlgoVerseApp, fundAlgoToApp
from algoverse.utils import getAlgodClient, getAppAddress


def main():
    client = getAlgodClient()
    print("=========================================")
    creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))
    print("Alice is a creator.")
    print("Validator's Address: ", creator.getAddress())

    try:
        print("=========================================")
        print("Deploying the smart contract....")
        app_id = createAlgoVerseApp(
            client=client,
            creator=creator
        )
        print("App ID: ", app_id)
        print("App Address:", getAppAddress(app_id))  # max apps per acct is 10
        print("=========================================")
        print("Funding Algo to the smart contract....")
        fundAlgoToApp(
            client=client,
            funder=creator,
            app_id=app_id,
        )

    except AlgodHTTPError:
        traceback.print_exc()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    main()
