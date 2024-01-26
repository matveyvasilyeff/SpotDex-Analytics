from tkinter import E
from typing import Dict
from unicodedata import name

from pyteal import *
import pyteal

_max_keys = 16
_page_size = 128 - 1  # need 1 byte for key
_max_bytes = _max_keys * _page_size
_max_bits = _max_bytes * 8

max_keys = Int(_max_keys)
page_size = Int(_page_size)
max_bytes = Int(_max_bytes)
orderByteSize = Int(27)
orderKeySize = Int(4) * orderByteSize

# @Subroutine(TealType.bytes)
# def intkey(i: TealType.uint64) -> Expr:
#     return Extract(Itob(i), Int(7), Int(1))

@Subroutine(TealType.anytype)
def local_get_else(acct: TealType.uint64, key: TealType.bytes, default: Expr) -> Expr:
    """Returns the result of a local storage MaybeValue if it exists, else return a default value"""
    mv = App.localGetEx(acct, Int(0), key)
    return Seq(mv, If(mv.hasValue()).Then(mv.value()).Else(default))


class UserAccount:
    
    def __init__(self):
        self.priceCoin_locked = ScratchVar(TealType.uint64)
        self.priceCoin_available = ScratchVar(TealType.uint64)
        self.baseCoin_locked = ScratchVar(TealType.uint64)
        self.baseCoin_available = ScratchVar(TealType.uint64)
        self.WLFeeWallet = ScratchVar(TealType.bytes)
        self.WLFeeShare = ScratchVar(TealType.uint64)
        self.WLCustomFee = ScratchVar(TealType.uint64)
        self.slotMap = ScratchVar(TealType.uint64)

        self.name_to_offset = {
            'priceCoin_locked': Int(0),
            'priceCoin_available': Int(8),
            'baseCoin_locked': Int(16),
            'baseCoin_available': Int(24),
            'WLFeeWallet': Int(32),
            'WLFeeShare': Int(64),
            'WLCustomFee': Int(72),
            'slotMap': Int(80)
        }
       
    def save(self, acct) -> Expr:
        account_info = ScratchVar(TealType.bytes)
        return Seq(
            account_info.store(Concat(
                Itob(self.priceCoin_locked.load()),
                Itob(self.priceCoin_available.load()),
                Itob(self.baseCoin_locked.load()),
                Itob(self.baseCoin_available.load()),
                self.WLFeeWallet.load(),
                Itob(self.WLFeeShare.load()),
                Itob(self.WLCustomFee.load()),
                Itob(self.slotMap.load()),
            )),
            App.localPut(acct, Bytes("accountInfo"), account_info.load())
        )
    
    def load(self, acct) -> Expr:
        account_bytes = ScratchVar(TealType.bytes)
        return Seq(
            account_bytes.store(App.localGet(acct, Bytes("accountInfo"))),
            self.priceCoin_locked.store(ExtractUint64(account_bytes.load(), self.name_to_offset["priceCoin_locked"])),
            self.priceCoin_available.store(ExtractUint64(account_bytes.load(), self.name_to_offset["priceCoin_available"])),
            self.baseCoin_locked.store(ExtractUint64(account_bytes.load(), self.name_to_offset["baseCoin_locked"])),
            self.baseCoin_available.store(ExtractUint64(account_bytes.load(), self.name_to_offset["baseCoin_available"])),
            self.WLFeeWallet.store(Extract(account_bytes.load(), self.name_to_offset["WLFeeWallet"], Int(32))),
            self.WLFeeShare.store(ExtractUint64(account_bytes.load(), self.name_to_offset["WLFeeShare"])),
            self.WLCustomFee.store(ExtractUint64(account_bytes.load(), self.name_to_offset["WLCustomFee"])),
            self.slotMap.store(ExtractUint64(account_bytes.load(), self.name_to_offset["slotMap"])),
       )


class Order:
    
    def __init__(self) -> None:        
        self.orderID = ScratchVar(TealType.uint64)
        self.side = ScratchVar(TealType.bytes)
        self.price = ScratchVar(TealType.uint64)
        self.amount = ScratchVar(TealType.uint64)
        self.type = ScratchVar(TealType.bytes)
        self.storageSlot = ScratchVar(TealType.uint64)
        self.slotMapUpdate = ScratchVar(TealType.uint64)
        
        self.name_to_offset = {
            'orderID': Int(0),
            #'status': Int(8),
            'side': Int(8),
            'price': Int(9),
            'amount': Int(17),
            'type': Int(25),    #  "0", "P", "I"
            'storageSlot': Int(26)
        }
        
    def save(self, acct, slotMap) -> Expr:
        local_key = ScratchVar(TealType.bytes)
        offset = ScratchVar(TealType.uint64)
        current_key_data = ScratchVar(TealType.bytes)
        return Seq(
            If(self.storageSlot.load() == Int(0)).Then(Seq(
                #slot is zero so It's a new order  
                #get the first available slot for the account from the slotMap
                self.storageSlot.store(BitLen(slotMap)),
                If(self.storageSlot.load() == Int(0)).Then(Seq(
                    Log(Bytes("storage_full")),
                    Reject()
                ))
            )),
            # calc. which key (1 to 15) and extract the one byte from uint64 
            local_key.store( Extract( Itob( ((self.storageSlot.load() - Int(1)) / Int(4)) ), Int(7), Int(1) ) ),
            # calc. slot# in key (1 to 4) - moved to calc directly where needed, to reduce opcodes
            #slot_in_kv.store(self.storageSlot.load() - (local_key.load() * Int(4))),
            # calculate byte offset start inside the key
            offset.store(orderByteSize * ((self.storageSlot.load() - (Btoi(local_key.load()) * Int(4))) - Int(1))),
            # read slot data
            current_key_data.store(local_get_else(acct, local_key.load(), Bytes("0"))),
            If(current_key_data.load() == Bytes("0")).Then(Seq(
                current_key_data.store(BytesZero(orderKeySize)),
            )),
            
            App.localPut(acct, local_key.load(), Concat(Substring(current_key_data.load(), Int(0), offset.load()), Concat(
                Itob(self.orderID.load()),
                #self.status.load(),
                self.side.load(),
                Itob(self.price.load()),
                Itob(self.amount.load()),
                self.type.load(),
                Extract(Itob(self.storageSlot.load()), Int(7), Int(1)),
            ), Substring(current_key_data.load(), offset.load() + orderByteSize, orderKeySize))),
            Log(Concat(Bytes("------order {") , Itob(self.orderID.load()), Bytes("} ------------"))),
            # unset slot bit in map
            self.slotMapUpdate.store(SetBit(slotMap, self.storageSlot.load()-Int(1), Int(0))), #this scratchvar is for new orders, and saved when account is saved during new order function, not inside order-save
        )
    
    def load(self, acct, storage_slot):
        orderBytestream = ScratchVar(TealType.bytes)
        local_key = ScratchVar(TealType.uint64)
        offset = ScratchVar(TealType.uint64)
        current_key_data = ScratchVar(TealType.bytes)
        return Seq(
            # calc. which key (1 to 15)
            local_key.store((storage_slot - Int(1)) / Int(4)),
            # calculate byte offset start inside the key
            offset.store(orderByteSize * ((storage_slot - (local_key.load() * Int(4))) - Int(1))),
            # read slot data
            current_key_data.store(local_get_else(acct, Extract(Itob(local_key.load()), Int(7), Int(1)), Bytes("0") )),
            If(current_key_data.load() == Bytes("0")).Then(Seq(
                #Order Not Found - FAIL TX
                Reject()
            )),
            # get the order from slot
            orderBytestream.store(Extract(current_key_data.load(), (orderByteSize * ((storage_slot - (local_key.load() * Int(4))) - Int(1))), orderByteSize)),
            # load order items
            self.orderID.store(ExtractUint64(orderBytestream.load(), self.name_to_offset["orderID"])),
            #self.status.store(Extract(orderBytestream.load(), self.name_to_offset["status"], Int(1))),
            self.side.store(Extract(orderBytestream.load(), self.name_to_offset["side"], Int(1))),
            self.price.store(ExtractUint64(orderBytestream.load(), self.name_to_offset["price"])),
            self.amount.store(ExtractUint64(orderBytestream.load(), self.name_to_offset["amount"])),
            self.type.store(Extract(orderBytestream.load(), self.name_to_offset["type"], Int(1))),
            self.storageSlot.store(storage_slot),
            Log(Concat(Bytes("\n-------load data "), Itob(storage_slot), Bytes("--------\n"))),
            Log(orderBytestream.load())
        )

