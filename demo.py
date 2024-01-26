from algosdk import *
from pyteal.ast import *

from account import Account
from utils import get_algod_client, get_app_local_state, is_opted_in_asset
from operations import create_app, optin_app, payment_transaction, get_app_call, create_asset, app_call_with_asset, app_call_with_algo


# user declared account mnemonics
user1 = {
    'mnemonic': "strategy device nuclear fan venture produce journey hip possible front weapon ride agent lens finger find strategy little swift valley hand crazy swing absorb clog",
    'address' : "VBPSZ7M7425KGVYYQKWKC6HZB65RNBYOXPEEVOIIQEDXFFVS56YYSNKMB4",
}

user2 = {
    'mnemonic': "inside wreck jewel fence feature negative game car aerobic hip kidney test foot antique kind snow tackle creek school loyal type action napkin able female",
    'address' : "RDF5ZO7F5UM37J3YZJPXIF5YN2CX52ZWIMRYMR2H73QA6FB2T765KCY2VE",
}

# only used to create smart contract
user3 = {
    'mnemonic': "mobile athlete submit balcony sausage satisfy ball cabin rich high repeat spike carbon spirit olympic horse world husband tragic near connect habit comfort about scissors",
    'address' : "EN24BSP6WLG2DI7WOZ45P4A2PHI5RKCGA4ZE4W3C6E3GCWBPOUU4ZCX4D4",
}


if __name__ == "__main__":
    
    algod_url = "http://localhost:4001"
    algod_api_key = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    
    client = get_algod_client(algod_url, algod_api_key)
    
    creator = Account.from_mnemonic(user3["mnemonic"])
    print(creator.get_address())
        
    sender = Account.from_mnemonic(user1["mnemonic"])
    print(sender.get_address())
    
    print("Create Asset A...")
    asset_a = create_asset(client, sender, "A", 3)
    print("Created asset a with id: {}".format(asset_a))
    
    # print("Create Asset B...")
    # asset_b = create_asset(client, sender, "B", 3)
    # print("Created asset b with id: {}".format(asset_b))
    
    pair_name = b"ALGO/USDT"
    base_name = b"ALGO"
    price_name = b"USDT"
    base_id = 0
    print("Create App...")
    app_id = create_app(client, creator, pair_name, base_name, price_name, 0, asset_a, 6, 6)
    prog_addr = logic.get_application_address(app_id)    
    print(f"app id: {app_id}")
    
    print("Sending funds to application")
    funding_amount = 1_002_000
    payment_transaction(client, creator, funding_amount, prog_addr, "funds")
    
    print("User 1 opting In......")
    optin_app(client, sender, app_id)
    
    user = Account.from_mnemonic(user2["mnemonic"])
    
    print("new order 1 with base asset")
    app_call_with_algo(client, sender, app_id, 20000, app_args=["new_order", "S", 2000, 5000, "0"])
    local_state = get_app_local_state(client, app_id, sender.get_address())
    print("local state of sender:")
    print(local_state)
    
    # check if asset_a is opted in app
    if not is_opted_in_asset(client, asset_a, prog_addr):
        get_app_call(client, sender, app_id, app_args=[b"asset_optin"], assets=[asset_a])
    
    # call group txn for new order
    print("new order 2 with asset_a")
    app_call_with_asset(client, sender, app_id, asset_a, 300000, app_args = ["new_order", "B", 2000, 8000, "P"])
    
    local_state = get_app_local_state(client, app_id, sender.get_address())
    print("local state of sender:")
    print(local_state)
    
    print("new order 3 without fund")
    get_app_call(client, sender, app_id, app_args = ["new_order", "B", 2, 5, "P"], assets=[asset_a], accounts=[user.get_address()])
    local_state = get_app_local_state(client, app_id, sender.get_address())
    print("local state of sender:")
    print(local_state)
    
    print("cancel order 1")
    get_app_call(client, sender, app_id, app_args = ["cancel_order", 1, 64], assets=[asset_a], accounts=[user.get_address()])
    local_state = get_app_local_state(client, app_id, sender.get_address())
    print("local state of sender:")
    print(local_state)
    
    print("new order 4 without fund")
    get_app_call(client, sender, app_id, app_args = ["new_order", "B", 2, 10, "0"], assets=[asset_a], accounts=[user.get_address()])
    local_state = get_app_local_state(client, app_id, sender.get_address())
    print("local state of sender:")
    print(local_state)
    
    print("withdraw ASA")
    get_app_call(client, sender, app_id, app_args = ["asset_withdraw"], assets=[asset_a], accounts=[user.get_address()])
    local_state = get_app_local_state(client, app_id, sender.get_address())
    print("local state of sender:")
    print(local_state)
    
    # print("new order 2")
    # get_app_call(client, sender, app_id, app_args = ["new_order", "B", 4, 15], assets=[asset_a], accounts=[user.get_address()])
    # local_state = get_app_local_state(client, app_id, sender.get_address())
    # print("local state of sender:")
    # print(local_state)
    
    # print("new order 3")
    # get_app_call(client, sender, app_id, app_args = ["new_order", "B", 5, 15], assets=[asset_a], accounts=[user.get_address()])
    # local_state = get_app_local_state(client, app_id, sender.get_address())
    # print("local state of sender:")
    # print(local_state)

    # print("new order 4")
    # get_app_call(client, sender, app_id, app_args = ["new_order", "B", 6, 15], assets=[asset_a], accounts=[user.get_address()])
    # local_state = get_app_local_state(client, app_id, sender.get_address())
    # print("local state of sender:")
    # print(local_state)

    # print("new order 5")
    # get_app_call(client, sender, app_id, app_args = ["new_order", "B", 7, 15], assets=[asset_a], accounts=[user.get_address()])
    # local_state = get_app_local_state(client, app_id, sender.get_address())
    # print("local state of sender:")
    # print(local_state)

    # print("MATCH ORDER")
    # get_app_call(client, sender, app_id, app_args = ["match_orders", 1, 2, 3, 4, 5], assets=[asset_a], accounts=[user.get_address()])
    # local_state = get_app_local_state(client, app_id, sender.get_address())
    # print("local state of sender:")
    # print(local_state)