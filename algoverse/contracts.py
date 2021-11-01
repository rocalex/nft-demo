from pyteal import *


class AlgoVerse:
    class Variables:
        higher_rarity_key = Bytes("higher")

    @staticmethod
    @Subroutine(TealType.none)
    def increase(key):
        return Seq(
            App.globalPut(key, App.globalGet(key) + Int(1)),
            Return()
        )

    @staticmethod
    @Subroutine(TealType.none)
    def decrease(key):
        return Seq(
            App.globalPut(key, App.globalGet(key) - Int(1)),
            Return()
        )

    @staticmethod
    @Subroutine(TealType.uint64)
    def check_amount_by_rarity(amount: Expr, rarity: Expr) -> Expr:
        """
        :param amount: int
        :param rarity: int
        :return: Int(0) / Int(1)
        """
        return Seq(
            If(And(rarity == Int(1), amount == Int(2))).Then(Return(Int(1))),
            If(And(rarity == Int(2), amount == Int(3))).Then(Return(Int(1))),
            If(And(rarity == Int(3), amount == Int(2))).Then(Return(Int(1))),
            Return(Int(0))
        )

    def on_create(self):
        return Seq(
            Approve(),
        )

    def on_setup(self):
        br = Txn.application_args[1]  # base rarity
        return Seq(
            App.globalPut(Btoi(Txn.assets[0]), br),

            # opt into NFT asset -- because you can't opt in if you're already opted in, this is what
            # we'll use to make sure the contract has been set up
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: Txn.assets[0],
                    TxnField.asset_receiver: Global.current_application_address(),
                }
            ),
            InnerTxnBuilder.Submit(),

            Approve(),
        )

    def on_replace(self):
        asset_to_burn = Txn.assets[0]
        r = Txn.application_args[1]  # given rarity
        amount = Btoi(Txn.application_args[2])  # amount
        status = App.globalGetEx(Txn.applications[0], Itob(asset_to_burn))
        return Seq(
            status,
            Assert(status.hasValue()),
            Assert(Btoi(status.value()) == Btoi(r)),
            Assert(AlgoVerse.check_amount_by_rarity(amount, Btoi(r))),

            # revoke given amount of assets
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: asset_to_burn,
                    TxnField.asset_receiver: Global.current_application_address(),
                    TxnField.asset_amount: Btoi(amount),
                    TxnField.asset_sender: Txn.sender(),
                }
            ),
            InnerTxnBuilder.Submit(),

            # create higher asset
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_total: Int(20),
                    TxnField.config_asset_decimals: Int(1),
                    TxnField.config_asset_unit_name: Concat(Bytes("President "), r),
                    TxnField.config_asset_name: Concat(Bytes("President "), r),
                    TxnField.config_asset_url: Bytes("https://gold.rush/"),
                    TxnField.config_asset_manager: Txn.sender(),
                    TxnField.config_asset_reserve: Txn.sender(),
                    TxnField.config_asset_freeze: Txn.sender(),
                    TxnField.config_asset_clawback: Global.current_application_address(),
                }
            ),
            InnerTxnBuilder.Submit(),

            # store the new asset id and rarity
            App.globalPut(Btoi(Txn.created_asset_id()), Itob(Btoi(r) + Int(1))),

            # transfer the new asset
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: Txn.created_asset_id(),
                    TxnField.asset_receiver: Txn.sender(),
                    TxnField.asset_amount: Int(1),
                }
            ),
            InnerTxnBuilder.Submit(),
            Approve()
        )

    def on_call(self):
        call_method = Txn.application_args[0]
        return Cond(
            [call_method == Bytes("setup"), self.on_setup()],
            [call_method == Bytes("replace"), self.on_replace()]
        )

    def on_opting_in(self):
        return Seq(
            Return(Int(1))
        )

    def on_delete(self):
        return Seq(
            Approve()
        )

    def application_start(self):
        actions = Cond(
            [Txn.application_id() == Int(0), self.on_create()],
            [Txn.on_completion() == OnComplete.NoOp, self.on_call()],
            [Txn.on_completion() == OnComplete.OptIn, self.on_opting_in()],
            [
                Txn.on_completion() == OnComplete.DeleteApplication,
                self.on_delete(),
            ],
            [
                Or(
                    Txn.on_completion() == OnComplete.OptIn,
                    Txn.on_completion() == OnComplete.CloseOut,
                    Txn.on_completion() == OnComplete.UpdateApplication,
                ),
                Reject(),
            ],
        )
        return actions

    def approval_program(self):
        return self.application_start()

    def clear_program(self):
        return Return(Int(1))


if __name__ == "__main__":
    contract = AlgoVerse()
    with open("algoverse_approval.teal", "w") as f:
        compiled = compileTeal(contract.approval_program(), mode=Mode.Application, version=5)
        f.write(compiled)

    with open("algoverse_clear_state.teal", "w") as f:
        compiled = compileTeal(contract.clear_program(), mode=Mode.Application, version=5)
        f.write(compiled)
