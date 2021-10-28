import os

import dotenv

from algoverse.account import Account
from algoverse.operations import closeAlgoVerseApp
from algoverse.utils import getAlgodClient


def main():
    client = getAlgodClient()
    creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))
    app_id = 41357655

    closeAlgoVerseApp(client, app_id, creator)


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    main()
