from pyteal import *


class AlgoVerse:
    class Variables:
        assets_cnt_key = Bytes("assets_cnt")

    @staticmethod
    @Subroutine(TealType.uint64)
    def get_asset_per_rarity(rarity: Expr) -> Expr:
        i = ScratchVar(TealType.uint64)
        a_r = ScratchVar(TealType.bytes)
        r = ScratchVar(TealType.uint64)
        a = ScratchVar(TealType.uint64)
        return Seq(
            For(i.store(Int(0)), i.load() < Txn.assets.length(), i.store(i.load() + Int(1))).Do(Seq(
                a_r.store(App.globalGet(Itob(i.load()))),
                a.store(Btoi(Substring(a_r.load(), Int(0), Int(7)))),
                r.store(Btoi(Substring(a_r.load(), Int(8), Len(a_r.load()) - Int(1)))),
                If(r.load() == rarity).Then(
                    Return(a.load())
                )
            )),
            Return(Int(0))
        )

    @staticmethod
    @Subroutine(TealType.uint64)
    def get_higher_asset(asset_id: Expr) -> Expr:
        i = ScratchVar(TealType.uint64)
        asset_rarity = ScratchVar(TealType.bytes)
        rarity_tmp = ScratchVar(TealType.uint64)
        asset_tmp = ScratchVar(TealType.uint64)
        cur_rarity = ScratchVar(TealType.uint64)
        return Seq(
            cur_rarity.store(Int(0)),
            For(i.store(Int(0)), i.load() < Txn.assets.length(), i.store(i.load() + Int(1))).Do(Seq(
                asset_rarity.store(App.globalGet(Itob(i.load()))),
                asset_tmp.store(Btoi(Substring(asset_rarity.load(), Int(0), Int(7)))),
                rarity_tmp.store(Btoi(Substring(asset_rarity.load(), Int(8), Len(asset_rarity.load()) - Int(1)))),
                If(asset_tmp.load() == asset_id).Then(
                    cur_rarity.store(rarity_tmp.load())
                )
            )),
            For(i.store(Int(0)), i.load() < Txn.assets.length(), i.store(i.load() + Int(1))).Do(Seq(
                asset_rarity.store(App.globalGet(Itob(i.load()))),
                asset_tmp.store(Btoi(Substring(asset_rarity.load(), Int(0), Int(7)))),
                rarity_tmp.store(Btoi(Substring(asset_rarity.load(), Int(8), Len(asset_rarity.load()) - Int(1)))),
                If(rarity_tmp.load() > cur_rarity.load()).Then(
                    Return(asset_tmp.load())
                )
            )),
            Return(Int(0))
        )

    def on_create(self):
        return Seq(
            Approve(),
        )

    def on_setup(self):
        i = ScratchVar(TealType.uint64)
        return Seq(
            App.globalPut(self.Variables.assets_cnt_key, Txn.assets.length()),
            For(i.store(Int(0)), i.load() < Txn.assets.length(), i.store(i.load() + Int(1))).Do(Seq(
                App.globalPut(
                    Itob(i.load()),
                    Concat(Itob(Txn.assets[i.load()]), Txn.application_args[i.load() + Int(1)])  # asset : rarity
                ),

                # opt into NFT asset -- because you can't opt in if you're already opted in, this is what
                # we'll use to make sure the contract has been set up
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
        rarity = Btoi(Txn.application_args[1])
        foreign_asset = Txn.assets[0]
        status = App.globalGetEx(Txn.applications[0], Itob(foreign_asset))
        return Seq(
            status,
            Assert(status.hasValue()),

            If(Txn.application_args.length() == Int(2)).Then(Seq(
                Assert(AlgoVerse.get_asset_per_rarity(rarity) != Int(0)),

                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: AlgoVerse.get_asset_per_rarity(rarity),
                        TxnField.asset_receiver: Txn.sender(),
                    }
                ),
                InnerTxnBuilder.Submit(),
            )).Else(Seq(
                Assert(AlgoVerse.get_higher_asset(rarity) != Int(0)),

                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields(
                    {
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: AlgoVerse.get_higher_asset(foreign_asset),
                        TxnField.asset_receiver: Txn.sender(),
                    }
                ),
                InnerTxnBuilder.Submit(),
            )),
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
