import os
import traceback

import dotenv
from algosdk.error import AlgodHTTPError

from algoverse.account import Account
from algoverse.testing.resources import createToken
from algoverse.utils import getAlgodClient


def main():
    client = getAlgodClient()
    creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))
    for _ in range(45):
        try:
            print("=========================================")
            print("Alice is generating an example token....")
            token_id = createToken(client, creator)
            print("The Token ID is:", token_id)
        except AlgodHTTPError:
            traceback.print_exc()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    main()
