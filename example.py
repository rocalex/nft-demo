import os
import random
import traceback
from typing import List

import dotenv
from algosdk.error import AlgodHTTPError
from algosdk.logic import get_application_address

from algoverse.account import Account
from algoverse.operations import BaseApp
from algoverse.testing.resources import createToken
from algoverse.utils import getAlgodClient, getAppAddress


class Asset:
    def __init__(self, pk: int = 0, rarity: int = 1):
        self.id = pk
        self.rarity = rarity  # 1: base, 2: silver, 3: gold, 4: diamond


class AlgoVerseExample(BaseApp):
    def __init__(self):
        super().__init__()
        self.client = getAlgodClient()
        self.creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))
        self.receiver = Account.FromMnemonic(os.environ.get('RECEIVER_MNEMONIC'))
        self.app_id = 0
        self.assets: List[Asset] = []
        self.amount = 20

    def create_example_assets(self):
        for _ in range(45):
            try:
                print("=========================================")
                print("Generating an example token....")
                token_id = createToken(self.client, self.creator, self.amount, get_application_address(self.app_id))
                print("The Token ID is:", token_id)
                self.assets.append(Asset(token_id, 1))

            except AlgodHTTPError:
                traceback.print_exc()

    def deploy_app(self):
        try:
            print("=========================================")
            print("Deploying the smart contract....")
            self.app_id = self.create_app(client=self.client, creator=self.creator)
            print("App ID: ", self.app_id)
            print("App Address:", getAppAddress(self.app_id))  # max apps per acct is 10

        except AlgodHTTPError:
            traceback.print_exc()

    def fund_assets(self):
        for asset in self.assets:
            try:
                print("=========================================")
                print("Funding Algo to the smart contract....")
                self.fund_algo_to_app(
                    client=self.client,
                    funder=self.creator,
                    app_id=self.app_id,
                )

                print("=========================================")
                print("Setting up the app....")
                self.setup_app(self.client, self.creator, self.app_id, asset.id, asset.rarity)
            except AlgodHTTPError:
                traceback.print_exc()

    def test_send_asset(self):
        asset = random.choice(self.assets)
        try:
            print("=========================================")
            print("Replacing token....")
            self.send_asset(self.client, self.creator, self.app_id, asset.id, asset.rarity, 2)
        except AlgodHTTPError:
            traceback.print_exc()

    def close_algoverse_app(self):
        try:
            print("=========================================")
            print("Closing the smart contract....")
            self.close_app(self.client, self.app_id, self.creator)
        except AlgodHTTPError:
            traceback.print_exc()

    def start(self):
        self.deploy_app()
        self.create_example_assets()
        self.fund_assets()
        self.test_send_asset()
        self.close_algoverse_app()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    AlgoVerseExample().start()
