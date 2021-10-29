import os
import random
import traceback

import dotenv
from algosdk.error import AlgodHTTPError

from algoverse.account import Account
from algoverse.operations import BaseApp
from algoverse.testing.resources import createNFT
from algoverse.utils import getAlgodClient, getAppAddress


class AlgoVerseExample(BaseApp):
    def __init__(self):
        super().__init__()
        self.client = getAlgodClient()
        self.creator = Account.FromMnemonic(os.environ.get('ACCOUNT_MNEMONIC'))
        self.receiver = Account.FromMnemonic(os.environ.get('RECEIVER_MNEMONIC'))
        self.app_id = 0
        self.asset_ids = []
        self.rarities = []
        self.total_assets = 45

    def create_example_assets(self):
        for _ in range(self.total_assets):
            try:
                print("=========================================")
                print("Generating an example token....")
                token_id = createNFT(self.client, self.creator)
                print("The Token ID is:", token_id)
                self.asset_ids.append(token_id)
                self.rarities.append(random.randint(0, 20))

            except AlgodHTTPError:
                traceback.print_exc()

    def deploy_app(self):
        try:
            print("=========================================")
            print("Deploying the smart contract....")
            self.app_id = self.create_app(client=self.client, creator=self.creator)
            print("App ID: ", self.app_id)
            print("App Address:", getAppAddress(self.app_id))  # max apps per acct is 10
            print("=========================================")
            print("Funding Algo to the smart contract....")
            self.fund_algo_to_app(client=self.client, funder=self.creator, app_id=self.app_id)

        except AlgodHTTPError:
            traceback.print_exc()

    def fund_assets(self):
        sub_rarities = []
        sub_assets = []
        rr = []
        aa = []
        for i in range(self.total_assets):
            if i % 8 == 0 and i != 0:
                rr.append(sub_rarities)
                rr.append(sub_assets)
                sub_rarities = []
                sub_assets = []
            if i == (self.total_assets - 1):
                rr.append(sub_rarities)
                aa.append(sub_assets)
            sub_rarities.append(self.rarities[i])
            sub_assets.append(self.asset_ids[i])

        for idx in range(len(rr)):
            sub_rarities = rr[idx]
            sub_assets = aa[idx]
            try:
                print("=========================================")
                print("Setting up the app....")
                self.setup_app(self.client, self.creator, self.app_id, sub_assets, sub_rarities)

                for asset_id in sub_assets:
                    print("=========================================")
                    print("Funding Algo to the smart contract....")
                    self.fund_algo_to_app(
                        client=self.client,
                        funder=self.creator,
                        app_id=self.app_id,
                    )

                    print("=========================================")
                    print("Funding token to app....")
                    self.fund_asset_to_app(
                        client=self.client,
                        app_id=self.app_id,
                        sender=self.creator,
                        asset_id=asset_id,
                        amount=1
                    )
            except AlgodHTTPError:
                traceback.print_exc()

    def test_replace_asset(self):
        try:
            print("=========================================")
            print("Generating an example token to replace....")
            token_id = createNFT(self.client, self.creator)
            rarity = random.randint(0, 20)
            print("The Token ID is:", token_id)
            print("Rarity: ", rarity)
            print("=========================================")
            print("Replacing token....")
            self.replace_asset(self.client, self.creator, self.app_id, token_id, rarity)

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
        self.test_replace_asset()
        self.close_algoverse_app()


if __name__ == '__main__':
    dotenv.load_dotenv('.env')
    AlgoVerseExample().start()
