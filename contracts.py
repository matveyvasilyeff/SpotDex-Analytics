from pyteal import *
from data_utils import *


user = {
    'mnemonic': "strategy device nuclear fan venture produce journey hip possible front weapon ride agent lens finger find strategy little swift valley hand crazy swing absorb clog",
    'address' : "VBPSZ7M7425KGVYYQKWKC6HZB65RNBYOXPEEVOIIQEDXFFVS56YYSNKMB4",
}

user2 = {
    'mnemonic': "inside wreck jewel fence feature negative game car aerobic hip kidney test foot antique kind snow tackle creek school loyal type action napkin able female",
    'address' : "RDF5ZO7F5UM37J3YZJPXIF5YN2CX52ZWIMRYMR2H73QA6FB2T765KCY2VE",
}

# only used to create smart contract
creator = {
    'mnemonic': "mobile athlete submit balcony sausage satisfy ball cabin rich high repeat spike carbon spirit olympic horse world husband tragic near connect habit comfort about scissors",
    'address' : "EN24BSP6WLG2DI7WOZ45P4A2PHI5RKCGA4ZE4W3C6E3GCWBPOUU4ZCX4D4",
}
   

def approval_program():
   # Mode.Application specifies that this is a smart contract   
    handle_noop = Cond(
        [Txn.application_args.length() == Int(0), Reject()],
        [Txn.application_args[0] == Bytes("asset_optin"), asset_opt_in()],
        [Txn.application_args[0] == Bytes("withdraw"), withdraw(Txn.assets[0])],
        [Txn.application_args[0] == Bytes("new_order"), new_order(Txn.application_args[1], Btoi(Txn.application_args[2]), Btoi(Txn.application_args[3]), Txn.application_args[4])],
        [Txn.application_args[0] == Bytes("match_orders"), match_orders(Txn.accounts[1], Btoi(Txn.application_args[1]), Btoi(Txn.application_args[2]), Txn.accounts[2], Btoi(Txn.application_args[3]), Btoi(Txn.application_args[4]), Btoi(Txn.application_args[5]))],
        [Txn.application_args[0] == Bytes("cancel_order"), cancel_order(Btoi(Txn.application_args[1]), Btoi(Txn.application_args[2]))],
        
        [ Int(1), Return(Int(1)) ]
    ) 
   
    on_creation = Seq([
        on_create(Txn.application_args[0], Txn.application_args[1], Txn.application_args[2], Txn.assets[0], Txn.assets[1], Btoi(Txn.application_args[3]), Btoi(Txn.application_args[4])),
        Approve()
    ])
   
    handle_optin = Seq([
        newAccount(),
        Approve()
    ])
    
    handle_closeout = Seq([
        closeout(),
        Approve(),
    ])

    handle_updateapp = Return(Int(1))

    handle_deleteapp = Return(Int(1))

    program = Cond(
        [Txn.application_id() == Int(0), on_creation],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp],
        [Txn.on_completion() == OnComplete.NoOp, handle_noop],
    )
    return compileTeal(program, Mode.Application, version=5)


def clear_state_program():
    program = Return(Int(1))
    # Mode.Application specifies that this is a smart contract
    return compileTeal(program, Mode.Application, version=5)


def on_create(pair_name, base_name, price_name, base_id, price_id, bcd, pcd):
    return Seq([
        App.globalPut(Bytes("Pair"), pair_name), # "ALGO/USDT"
        App.globalPut(Bytes("DECIMALS"), Int(8)),
        App.globalPut(Bytes("BaseCurrency"), base_name), # "ALGO"
        App.globalPut(Bytes("PriceCurrency"), price_name), # "USDT" 
        App.globalPut(Bytes("BaseCurrencyId"), base_id), # asset id (0 for Algo, assetId for ASA)
        App.globalPut(Bytes("PriceCurrencyId"), price_id), # asset id (0 for Algo, assetId for ASA)
        App.globalPut(Bytes("BaseCurrencyDecimals"), bcd), # decimal value accepted by this base currency
        App.globalPut(Bytes("PriceCurrencyDecimals"), pcd), # decimal value accepted by this price currency
        # App.globalPut(Bytes("Min_Price_Inc"), Int(100000000)),#10^8
        # App.globalPut(Bytes("Min_Size_Inc"), Int(1000000)),#10^8
        # App.globalPut(Bytes("Min_Order_Size"), Int(1000000)),#10^8
        # App.globalPut(Bytes("trading_Fee"), Int(3000000)),#10^8
        App.globalPut(Bytes("order_counter"), Int(0)),
        Approve()
    ])
    

def closeout():
    acct = UserAccount()
    refund_algo = ScratchVar(TealType.uint64)
    return Seq([
        # move all locked balances to available, send all from available balance funds to user, delete all local keys,
        acct.load(Txn.sender()),
        refund_algo.store(Int(0)),
        acct.priceCoin_available.store(acct.priceCoin_available.load() + acct.priceCoin_locked.load()),
        # acct.priceCoin_locked.store(Int(0)),
        acct.baseCoin_available.store(acct.baseCoin_available.load() + acct.baseCoin_locked.load()),
        If (acct.priceCoin_available.load() > Int(0)).Then(Seq(
            If (App.globalGet(Bytes("PriceCurrencyId")) == Int(0)).Then(Seq(
                refund_algo.store(refund_algo.load() + acct.priceCoin_available.load()),
            )).Else(Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields({
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: App.globalGet(Bytes("PriceCurrencyId")),
                        TxnField.asset_amount: acct.priceCoin_available.load(),
                        TxnField.asset_receiver: Txn.sender(),
                    }),
                InnerTxnBuilder.Submit(),
            )),
        )),
        
        If (acct.baseCoin_available.load() > Int(0)).Then(Seq(
            If (App.globalGet(Bytes("BaseCurrencyId")) == Int(0)).Then(Seq(
                refund_algo.store(refund_algo.load() + acct.baseCoin_available.load()),                
            )).Else(Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields({
                        TxnField.type_enum: TxnType.AssetTransfer,
                        TxnField.xfer_asset: App.globalGet(Bytes("BaseCurrencyId")),
                        TxnField.asset_amount: acct.baseCoin_available.load(),
                        TxnField.asset_receiver: Txn.sender(),
                    }),
                InnerTxnBuilder.Submit(),
            )),
        )),
        
        If (refund_algo.load() > Int(0)).Then(Seq(
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.asset_amount: refund_algo.load(),
                    TxnField.asset_receiver: Txn.sender(),
            }),
            InnerTxnBuilder.Submit(),
        )),
        
        acct.slotMap.store(Int(0)),
        acct.save(Txn.sender()),
        App.localDel(Txn.sender(), Bytes("accountInfo")),
        
        Approve()
    ])


def newAccount():
    user = UserAccount()
    return Seq([
        user.priceCoin_locked.store(Int(0)),
        user.priceCoin_available.store(Int(1000)),
        user.baseCoin_locked.store(Int(0)),
        user.baseCoin_available.store(Int(0)),
        user.WLFeeWallet.store(BytesZero(Int(32))),
        user.WLFeeShare.store(Int(0)),
        user.WLCustomFee.store(Int(0)),
        user.slotMap.store(Int(18446744073709551600)),
        user.save(Txn.sender()),
        App.globalPut(Bytes("account_counter"), App.globalGet(Bytes("account_counter")) + Int(1)),
    ])


def asset_opt_in():
    asset = Txn.assets[0]
    return Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset,
                TxnField.asset_amount: Int(0),
                TxnField.asset_receiver: Global.current_application_address(),
                # TxnField.fee: Int(1000),
            }),
        InnerTxnBuilder.Submit(),
                
        Approve()                      
    ])


def new_order(Side, Price, Amount, Type):
    order_counter = App.globalGet(Bytes("order_counter"))
    order_counter = order_counter + Int(1)
    acct = UserAccount()
    order = Order()
    has_balance = AssetHolding.balance(Global.current_application_address(), Gtxn[0].xfer_asset())

    asset_name = ScratchVar(TealType.bytes)
    final_available = ScratchVar(TealType.uint64)
    amount_to_lock = ScratchVar(TealType.uint64)
    xfer_asset_id = ScratchVar(TealType.uint64)
    xfer_asset_amount = ScratchVar(TealType.uint64)
    
    return Seq([
        Assert(Or(Side == Bytes("B"), Side == Bytes("S"))),
        Assert(And(Price > Int(0), Amount > Int(0))),
        Assert(Or(Type == Bytes("0"), Type == Bytes("P"), Type == Bytes("I"))),
        # TODO
        # Check if group tx contained asset deposit
        Assert(Or(Gtxn[0].type_enum() == TxnType.AssetTransfer, Gtxn[0].type_enum() == TxnType.Payment, Gtxn[0].type_enum() == TxnType.ApplicationCall)),
        # Check if deposited asset correlates to one of the two pair assets        
        # If both yes, the update account available balance of the deposited asset
        # Update code to deal with fixed point arithmetics to make sure asset values are calculated accurately
        
        # Deposit >>>>>>>>>>---------------------------
        acct.load(Gtxn[0].sender()),
        If (Not(Gtxn[0].type_enum() == TxnType.ApplicationCall)).Then(Seq(
            # check length of array
            Assert(Global.group_size() == Int(2)),            
        
            # validate that xfer tx and app-call tx are the same sender
            Assert(Gtxn[0].sender() == Gtxn[1].sender()),
            
            If (Gtxn[0].type_enum() == TxnType.Payment).Then(Seq(
                # validate txn sent payment to the application contract address
                Assert(Global.current_application_address() == Gtxn[0].receiver()),
                xfer_asset_id.store(Int(0)),
                xfer_asset_amount.store(Gtxn[0].amount()),
                
            )).Else(Seq(    # deposit txn asset != ALGO
                # validate txn sent payment to the application contract address
                Assert(Global.current_application_address() == Gtxn[0].asset_receiver()),
                # price asset
                has_balance,
                Assert(has_balance.hasValue()), # Check if deposited asset correlates to one of the two pair assets
                xfer_asset_id.store(Gtxn[0].xfer_asset()),
                xfer_asset_amount.store(Gtxn[0].asset_amount()),                
            )),
            
            # check base/price by Buy and Sell
            If (Side == Bytes("B")).Then(Seq(
                Assert(App.globalGet(Bytes("PriceCurrencyId")) ==  xfer_asset_id.load()),
                acct.priceCoin_available.store(acct.priceCoin_available.load() + xfer_asset_amount.load()),
                asset_name.store(App.globalGet(Bytes("PriceCurrency"))),
                final_available.store(acct.priceCoin_available.load()),
            )).Else(Seq(
                Assert(App.globalGet(Bytes("BaseCurrencyId")) ==  xfer_asset_id.load()),
                acct.baseCoin_available.store(acct.baseCoin_available.load() + xfer_asset_amount.load()),
                asset_name.store(App.globalGet(Bytes("BaseCurrency"))),
                final_available.store(acct.baseCoin_available.load()),
            )),
            
            # export Log
            Log(Bytes("deposit")),
            Log(App.globalGet(Bytes("Pair"))),
            Log(asset_name.load()),
            Log(Itob(xfer_asset_amount.load())),
            Log(Itob(final_available.load())), 
        )).Else(Seq(
            # check length of array
            Assert(Global.group_size() == Int(1)),
        )),        
        # create order >>>>>>>>>>>>>-------
        order.orderID.store(order_counter),        
        #order.status.store(Bytes("0")),
        order.side.store(Side),
        order.price.store(Price),
        order.amount.store(Amount),
        order.type.store(Type),
        order.storageSlot.store(Int(0)),
        If(Side == Bytes("S")).Then(Seq(
            amount_to_lock.store(Amount),
            Assert(acct.baseCoin_available.load() >= amount_to_lock.load()),
            acct.baseCoin_available.store(acct.baseCoin_available.load() - amount_to_lock.load()),
            acct.baseCoin_locked.store(acct.baseCoin_locked.load() + amount_to_lock.load()),
            final_available.store(acct.baseCoin_available.load()),
        )).ElseIf(Side == Bytes("B")).Then(Seq(
            amount_to_lock.store(Price * Amount / (Int(10) ** App.globalGet(Bytes("BaseCurrencyDecimals")))),
            Assert(acct.priceCoin_available.load() >= amount_to_lock.load()),
            acct.priceCoin_available.store(acct.priceCoin_available.load() - amount_to_lock.load()),
            acct.priceCoin_locked.store(acct.priceCoin_locked.load() + amount_to_lock.load()),
            final_available.store(acct.priceCoin_available.load()),
        )).Else(Seq(
            Reject()
        )),

        order.save(Gtxn[0].sender(), acct.slotMap.load()), #Save New Order - MUST SAVE BEFORE ACC to create updated slotMap (updating account inside save costs too many opcodes)
        acct.slotMap.store(order.slotMapUpdate.load()), #Update slotMap in account from the new order
        acct.save(Gtxn[0].sender()), #Save Account - MUST SAVE ACC AFTER SAVING NEW ORDER!
        App.globalPut(Bytes("order_counter"), order_counter),
        
        # Log
        Log(Bytes("newOrder")),
        Log(App.globalGet(Bytes("Pair"))),
        Log(Itob(order.orderID.load())),
        Log(Itob(order.price.load())),
        Log(Itob(order.amount.load())),
        Log(order.side.load()),
        Log(Gtxn[0].sender()),
        Log(Itob(amount_to_lock.load())),
        Log(Itob(final_available.load())),
        
        Approve()
    ])


def match_orders(o1_acc, o1_id, o1_slot, o2_acc, o2_id, o2_slot, trade_amount):
    
    buyAcct = UserAccount()
    sellAcct = UserAccount()
    buyOrder = Order()
    sellOrder = Order()
    tmpOrder = Order()
    buyertm = ScratchVar(TealType.bytes)
    total = ScratchVar(TealType.uint64)
    tradePrice = ScratchVar(TealType.uint64)
    refund = ScratchVar(TealType.uint64)
    buyer = ScratchVar(TealType.bytes)
    seller = ScratchVar(TealType.bytes)
    return Seq([        
        tmpOrder.load(o1_acc, o1_slot),
        # verify order IDs and difference orders between two orders
        # Assert(And(buyOrder.orderID.load() == o1_id, sellOrder.orderID.load() == o2_id, Not(buyOrder.side.load()==sellOrder.side.load()))),
        If (tmpOrder.side.load() == Bytes("S")).Then(Seq(
            # change buyorder and sellorder
            buyer.store(o2_acc),
            seller.store(o1_acc),
            buyAcct.load(o2_acc), #load account
            sellAcct.load(o1_acc),
            buyOrder.load(buyer.load(), o2_slot),
            sellOrder.load(seller.load(), o1_slot),
        )).Else(Seq(
            buyer.store(o1_acc),
            seller.store(o2_acc),
            buyAcct.load(o1_acc), #load account
            sellAcct.load(o2_acc),
            buyOrder.load(buyer.load(), o1_slot),
            sellOrder.load(seller.load(), o2_slot),
        )),
        
        # Check which is taker and maker by comparing orderID. Lower orderID is maker.
        If (buyOrder.orderID.load() < sellOrder.orderID.load()).Then(Seq(
            buyertm.store(Bytes("M")),
            tradePrice.store(buyOrder.price.load()),
        )).Else(Seq(
            tradePrice.store(sellOrder.price.load()),
        )),
        
        Assert(buyOrder.price.load() >= sellOrder.price.load()),
        
        Assert(And(buyOrder.amount.load() >= trade_amount, sellOrder.amount.load() >= trade_amount)),
        
        total.store(trade_amount * tradePrice.load()/(Int(10) ** App.globalGet(Bytes("BaseCurrencyDecimals")))),
        
        refund.store(buyOrder.price.load() * trade_amount / (Int(10) ** App.globalGet(Bytes("BaseCurrencyDecimals"))) - total.load()),
        
        # Update balance of Buyer:
        buyAcct.priceCoin_available.store(buyAcct.priceCoin_available.load() + refund.load()),
        buyAcct.priceCoin_locked.store(buyAcct.priceCoin_locked.load() - (total.load()- refund.load())),
        buyAcct.baseCoin_available.store(buyAcct.baseCoin_available.load() + trade_amount),
        
        # Update balance of seller:
        sellAcct.priceCoin_available.store(sellAcct.priceCoin_available.load() + total.load()),
            # sellAcct.priceCoin_locked.store(),
            # sellAcct.baseCoin_available.store(),
        sellAcct.baseCoin_locked.store(sellAcct.baseCoin_locked.load() - trade_amount),
            
        # if tradeAmt == buyOrder.Amt
        If (trade_amount == buyOrder.amount.load()).Then(Seq(
            # remove order (buy)
            # set zero order and save
            buyOrder.orderID.store(Int(0)),
            buyOrder.side.store(Bytes("0")),
            buyOrder.price.store(Int(0)),
            buyOrder.amount.store(Int(0)),
            buyOrder.type.store(Bytes("0")),            
            # update account slotmap
            buyAcct.slotMap.store(SetBit(buyAcct.slotMap.load(), buyOrder.storageSlot.load()-Int(1), Int(1))), #Update slotMap in account from the new order
        )).Else(Seq(
            # updateOrder (buyOrder.Amt - tradeAmt)
            buyOrder.amount.store(buyOrder.amount.load() - trade_amount),            
        )),
        buyOrder.save(buyer.load(), buyOrder.storageSlot.load()),
        buyAcct.save(buyer.load()), #Save Account - MUST SAVE ACC AFTER SAVING NEW ORDER!
            
        If (trade_amount == sellOrder.amount.load()).Then(Seq(
            # remove order(Sell) & update slot
            # set zero order and save
            sellOrder.orderID.store(Int(0)),
            sellOrder.side.store(Bytes("0")),
            sellOrder.price.store(Int(0)),
            sellOrder.amount.store(Int(0)),
            sellOrder.type.store(Bytes("0")),
            # update account slotmap
            sellAcct.slotMap.store(SetBit(sellAcct.slotMap.load(), sellOrder.storageSlot.load()-Int(1), Int(1))), #Update slotMap in account from the new order
        )).Else(Seq( 
            # updateOrder (sellOrder.Amt - tradeAmt)
            sellOrder.amount.store(sellOrder.amount.load() - trade_amount),            
        )),
        sellOrder.save(seller.load(), sellOrder.storageSlot.load()),
        sellAcct.save(buyer.load()), #Save Account - MUST SAVE ACC AFTER SAVING NEW ORDER!
    
        # Log
        Log(Bytes("match_order")),
        Log(Itob(buyOrder.orderID.load())),
        Log(Itob(sellOrder.orderID.load())),
        Log(Itob(trade_amount)),
        Log(Itob(tradePrice.load())),
        Log(Itob(buyAcct.priceCoin_available.load())),
        Log(Itob(buyAcct.priceCoin_locked.load())),
        Log(Itob(buyAcct.baseCoin_available.load())),
        Log(Itob(sellAcct.baseCoin_locked.load())),
        Log(Itob(sellAcct.priceCoin_available.load())),
       
        Approve(),
    ])


def withdraw(asset_id):
    # receiver_addr = (user2["address"])
    acct = UserAccount()
    amount = ScratchVar(TealType.uint64)
    asset_name = ScratchVar(TealType.bytes)
    return Seq([
        acct.load(Txn.sender()),
        # check if asset is price/base
        If (App.globalGet(Bytes("PriceCurrencyId")) == asset_id).Then(Seq(
            asset_name.store(App.globalGet(Bytes("PriceCurrency"))),
            amount.store(acct.priceCoin_available.load()),            
            acct.priceCoin_available.store(Int(0))
        )).ElseIf(App.globalGet(Bytes("BaseCurrencyId")) == asset_id).Then(Seq(
            asset_name.store(App.globalGet(Bytes("BaseCurrency"))),
            amount.store(acct.baseCoin_available.load()),
            acct.baseCoin_available.store(Int(0))
        )).Else(Seq(
            Reject()
        )),
        
        Assert(amount.load() > Int(0)),
        # withdrawal asset is ALGO
        If (asset_id == Int(0)).Then(Seq(                
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.asset_amount: amount.load(),
                TxnField.asset_receiver: Txn.sender()
            }),
            InnerTxnBuilder.Submit(),                        
        )).Else(Seq( # withdrawal asset is ASA
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: asset_id,
                TxnField.asset_amount: amount.load(),
                TxnField.asset_receiver: Txn.sender()
            }),
            InnerTxnBuilder.Submit(),
        )),
        
        # save updated account
        acct.save(Txn.sender()),
        # Log
        Log(Bytes("withdraw")),
        Log(App.globalGet(Bytes("Pair"))),
        Log(asset_name.load()),
        Log(Itob(amount.load())),

        Approve()
    ])
    

def cancel_order(orderId, storageSlot):
    order = Order()
    acct = UserAccount()
    amount_to_release = ScratchVar(TealType.uint64)
    return Seq([
        acct.load(Txn.sender()),
        order.load(Txn.sender(), storageSlot),
        # verify orderID
        Assert(orderId == order.orderID.load()),
        # move locked balance to available balance (decide which asset Base/Price based on order SIDE)
        If(order.side.load() == Bytes("S")).Then(Seq(
            amount_to_release.store(order.amount.load()),
            acct.baseCoin_available.store(acct.baseCoin_available.load() + amount_to_release.load()),
            acct.baseCoin_locked.store(acct.baseCoin_locked.load() - amount_to_release.load()),
        )).ElseIf(order.side.load() == Bytes("B")).Then(Seq(
            amount_to_release.store(order.amount.load() * order.price.load()/(Int(10)**App.globalGet(Bytes("BaseCurrencyDecimals")))),
            acct.priceCoin_available.store(acct.priceCoin_available.load() + amount_to_release.load()),
            acct.priceCoin_locked.store(acct.priceCoin_locked.load() - amount_to_release.load()),
        )).Else(Seq(
            Reject()
        )),
        # set zero order and save
        order.orderID.store(Int(0)),
        #order.status.store(Bytes("0")),
        order.side.store(Bytes("0")),
        order.price.store(Int(0)),
        order.amount.store(Int(0)),
        order.type.store(Bytes("O")),
        order.save(Txn.sender(), acct.slotMap.load()),
        # update account slotmap
        acct.slotMap.store(SetBit(acct.slotMap.load(), storageSlot-Int(1), Int(1))), #Update slotMap in account from the new order
        acct.save(Gtxn[0].sender()), #Save Account - MUST SAVE ACC AFTER SAVING NEW ORDER!
        
        # Log
        Log(Bytes("cancelOrder")),
        Log(App.globalGet(Bytes("Pair"))),
        Log(Itob(orderId)),
        Log(Itob(order.price.load())),
        Log(Itob(order.amount.load())),
        Log(order.side.load()),
        Log(Itob(amount_to_release.load())),
        Log(Itob(acct.baseCoin_available.load())),
        Log(Itob(acct.baseCoin_locked.load())),
        Log(Itob(acct.priceCoin_available.load())),
        Log(Itob(acct.priceCoin_locked.load())),
        Approve()
    ])