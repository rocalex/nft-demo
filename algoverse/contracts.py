from pyteal import *


class AlgoVerse:
    class Variables:
        assets_cnt_key = Bytes("assets_cnt")
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
    def get_higher_rarity(asset_id: Expr, rarity: Expr):
        rarities = App.globalGet(Itob(asset_id))
        r1 = Substring(rarities, Int(0), Int(8))
        r2 = Substring(rarities, Int(8), Int(16))
        r3 = Substring(rarities, Int(16), Int(24))
        return Seq(
            If(Btoi(rarity) > Btoi(r3)).Then(
                Return(Int(0))
            ).ElseIf(And(Btoi(r3) >= Btoi(rarity), Btoi(rarity) > Btoi(r2))).Then(Seq(
                App.globalPut(AlgoVerse.Variables.higher_rarity_key, r3),
                Return(Int(1))
            )).ElseIf(And(Btoi(r2) >= Btoi(rarity), Btoi(rarity) > Btoi(r1))).Then(Seq(
                App.globalPut(AlgoVerse.Variables.higher_rarity_key, r2),
                Return(Int(1))
            )).ElseIf(Btoi(r1) >= Btoi(rarity)).Then(Seq(
                App.globalPut(AlgoVerse.Variables.higher_rarity_key, r1),
                Return(Int(1))
            )),
            Return(Int(0))
        )

    def on_create(self):
        return Seq(
            App.globalPut(self.Variables.assets_cnt_key, Int(0)),
            Approve(),
        )

    def on_setup(self):
        rb = Txn.application_args[1]  # base rarity
        r1 = Txn.application_args[2]
        r2 = Txn.application_args[3]
        r3 = Txn.application_args[4]
        return Seq(
            App.globalPut(
                App.globalGet(self.Variables.assets_cnt_key),
                Concat(Itob(Txn.assets[0]), rb, r1, r2, r3)  # asset : rarity
            ),

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

            AlgoVerse.increase(self.Variables.assets_cnt_key),

            Approve(),
        )

    def on_replace(self):
        foreign_asset = Txn.assets[0]
        r = Txn.application_args[1]  # given rarity
        amount = Btoi(Txn.application_args[2])  # amount
        status = App.globalGetEx(Txn.applications[0], Itob(foreign_asset))
        return Seq(
            status,
            Assert(status.hasValue()),
            Assert(AlgoVerse.get_higher_rarity(foreign_asset, r) == Int(1)),

            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: foreign_asset,
                    TxnField.asset_receiver: Txn.sender(),
                    TxnField.asset_amount: Btoi(amount)
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
