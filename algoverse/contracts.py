from pyteal import *


class AlgoVerse:
    class Variables:
        asset_cnt_key = Bytes("asset_cnt")

    @staticmethod
    @Subroutine(TealType.none)
    def increase(key: Expr) -> Expr:
        return Seq(
            App.globalPut(key, App.globalGet(key) + Int(1)),
            Return()
        )

    @staticmethod
    @Subroutine(TealType.none)
    def decrease(key: Expr) -> Expr:
        return Seq(
            App.globalPut(key, App.globalGet(key) - Int(1)),
            Return()
        )

    @staticmethod
    @Subroutine(TealType.uint64)
    def check_if_asset_and_higher_exist(asset_id: Expr, higher_asset_id: Expr) -> Expr:
        """
        :param asset_id: int
        :param higher_asset_id: int
        :return: Int(0) / Int(1)
        """
        asset_cnt = Btoi(App.globalGet(AlgoVerse.Variables.asset_cnt_key))
        i = ScratchVar(TealType.uint64)
        return Seq(
            # App.globalPut(key, App.globalGet(key) - Int(1)),
            For(i.store(Int(0)), i.load() < asset_cnt, i.store(i.load() + Int(1))).Do(Seq(
                If(Or(
                    And(
                        BytesEq(Substring(App.globalGet(Itob(i.load())), Int(0), Int(8)), Itob(asset_id)) == Int(1),
                        BytesEq(Substring(App.globalGet(Itob(i.load())), Int(8), Int(16)),
                                Itob(higher_asset_id)) == Int(1)
                    ),
                    And(
                        BytesEq(Substring(App.globalGet(Itob(i.load())), Int(8), Int(16)), Itob(asset_id)) == Int(1),
                        BytesEq(Substring(App.globalGet(Itob(i.load())), Int(16), Int(24)),
                                Itob(higher_asset_id)) == Int(1)
                    ),
                    And(
                        BytesEq(Substring(App.globalGet(Itob(i.load())), Int(16), Int(24)), Itob(asset_id)) == Int(1),
                        BytesEq(Substring(App.globalGet(Itob(i.load())), Int(24), Int(32)),
                                Itob(higher_asset_id)) == Int(1)
                    )
                )).Then(
                    Return(Int(1))
                )
            )),
            Return(Int(0))
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
            App.globalPut(self.Variables.asset_cnt_key, Int(0)),
            Approve(),
        )

    def on_setup(self):
        i = ScratchVar(TealType.uint64)
        return Seq(
            App.globalPut(App.globalGet(self.Variables.asset_cnt_key),
                          Concat(Itob(Txn.assets[0]), Itob(Txn.assets[1]), Itob(Txn.assets[2]), Itob(Txn.assets[3]))),
            self.increase(self.Variables.asset_cnt_key),

            # opt into NFT asset -- because you can't opt in if you're already opted in, this is what
            # we'll use to make sure the contract has been set up
            For(i.store(Int(0)), i.load() < Txn.assets.length(), i.store(i.load() + Int(1))).Do(Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: Txn.assets[i.load()],
                        TxnField.asset_receiver: Global.current_application_address(),
                    }
                ),
                InnerTxnBuilder.Submit(),
            )),
            Approve(),
        )

    def on_replace(self):
        asset = Txn.assets[0]
        higher_asset = Txn.assets[1]  # higher asset
        r = Txn.application_args[1]  # given rarity
        amount = Btoi(Txn.application_args[2])  # amount
        return Seq(

            Assert(AlgoVerse.check_amount_by_rarity(amount, Btoi(r))),
            Assert(AlgoVerse.check_if_asset_and_higher_exist(asset, higher_asset)),

            # revoke given amount of assets
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: asset,
                    TxnField.asset_receiver: Global.current_application_address(),
                    TxnField.asset_amount: amount,
                    TxnField.asset_sender: Txn.sender(),
                }
            ),
            InnerTxnBuilder.Submit(),

            # transfer the higher asset
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: higher_asset,
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
