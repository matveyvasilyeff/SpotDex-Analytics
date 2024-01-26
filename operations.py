from typing import Tuple
from algosdk.future import transaction
from algosdk.v2client.algod import AlgodClient
from algosdk.logic import get_application_address
from typing import Optional
from account import Account
from contracts import *
from utils import fully_compile_contract, wait_for_transaction, get_app_global_state


def create_app(client: AlgodClient, sender: Account, pair_name, base_name:str, price_name:str, base_id:int, price_id:int, bcd:int, pcd:int) -> int:
    approval_program, clear_program = get_contracts(client)

    global_schema = transaction.StateSchema(32, 32)
    # num_byte_slice = 16 to store max orders
    local_schema = transaction.StateSchema(0, 16)
    
    txn = transaction.ApplicationCreateTxn(
        sender=sender.get_address(),
        sp=client.suggested_params(),
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program,
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=[pair_name, base_name, price_name, bcd.to_bytes(8, 'big'), pcd.to_bytes(8, 'big')],
        foreign_assets=[base_id, price_id],
        extra_pages=1
    )
    signed_txn = txn.sign(sender.get_private_key())
    tx_id = client.send_transaction(signed_txn)

    response = wait_for_transaction(client, tx_id)
    assert response.application_index is not None and response.application_index > 0
    return response.application_index


def optin_app(client: AlgodClient, sender: Account, app_id: int):
    txn = transaction.ApplicationOptInTxn(
        sender=sender.get_address(),
        sp=client.suggested_params(),
        index=app_id
    )
    signed_txn = txn.sign(sender.get_private_key())
    tx_id = client.send_transaction(signed_txn)
    wait_for_transaction(client, tx_id)


def fund_if_needed(client: AlgodClient, funder: str, pk: str, app: str):
    fund = False
    try:
        ai = client.account_info(app)
        fund = ai["amount"] < 1e7
    except:
        fund = True

    if fund:
        # Fund App address
        sp = client.suggested_params()
        txn_group = [transaction.PaymentTxn(funder, sp, app, 10000000)]
        return send(client, "seed", [txn.sign(pk) for txn in txn_group])
    
    
def payment_transaction(algod_client: AlgodClient, account: Account, amt, rcv, name):
    txn_group = [transaction.PaymentTxn(
        sender=account.get_address(), 
        sp=algod_client.suggested_params(),
        receiver=rcv,
        amt=amt)]
    
    return send(algod_client, name, [txn.sign(account.get_private_key()) for txn in txn_group])


def asa_opt_in(algod_client: AlgodClient, sender: Account, asa_id) -> Optional[str]:
    
    key = sender.get_private_key()

    txn_group = [transaction.AssetTransferTxn(
        sender=sender.get_address(),
        sp=algod_client.suggested_params(),
        receiver=sender.get_address(),
        amt=0,
        index=asa_id)]
    
    return send(algod_client, "opt_in", [txn.sign(key) for txn in txn_group])
    
    
def send(client: AlgodClient, name, signed_group):
    print(f"Sending Transaction for {name}")
    txid = client.send_transactions(signed_group)
    response = wait_for_transaction(client, txid)
    print(response.logs)
    return response                             # return transaction.wait_for_confirmation(client, txid, 5)


def app_call_with_algo(client: AlgodClient, sender: Account, app_id: int, amount: int , app_args=[]):
    print("---------- Group Txn New Order calling -----------")
    payment_txn = transaction.PaymentTxn(
        sender=sender.get_address(), 
        sp=client.suggested_params(),
        receiver=get_application_address(app_id),
        amt=amount)
    call_txn = transaction.ApplicationCallTxn(
        sender=sender.get_address(),
        sp=client.suggested_params(),
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=app_args
    )
    
    transaction.assign_group_id([payment_txn, call_txn])
    
    signed_payment_txn = payment_txn.sign(sender.get_private_key())
    signed_call_txn = call_txn.sign(sender.get_private_key())
    signedtxns = [signed_payment_txn, signed_call_txn]
    ids = [stxn.get_txid() for stxn in signedtxns]
    tx_id = client.send_transactions(signedtxns)
    
    response = [wait_for_transaction(client, tx_id) for tx_id in ids]
    # print(f" >> first txn log >> {response[0].logs}")
    print(f" >> second txn log >> {response[1].logs}")
    
    
def app_call_with_asset(client: AlgodClient, sender: Account, app_id: int, asset_id: int, amount: int , app_args=[]):
    print("---------- Group Txn New Order calling -----------")
    axfer_txn = transaction.AssetTransferTxn(
        sender=sender.get_address(),
        sp=client.suggested_params(),
        receiver=get_application_address(app_id),
        amt=amount,
        index=asset_id
    )
    call_txn = transaction.ApplicationCallTxn(
        sender=sender.get_address(),
        sp=client.suggested_params(),
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=app_args,
        foreign_assets=[asset_id]
    )
    
    transaction.assign_group_id([axfer_txn, call_txn])
    
    signed_axfer_txn = axfer_txn.sign(sender.get_private_key())
    signed_call_txn = call_txn.sign(sender.get_private_key())
    signedtxns = [signed_axfer_txn, signed_call_txn]
    ids = [stxn.get_txid() for stxn in signedtxns]
    tx_id = client.send_transactions(signedtxns)
    
    response = [wait_for_transaction(client, tx_id) for tx_id in ids]
    print(f" >> second txn log >> {response[1].logs}")


def get_app_call(client: AlgodClient, addr: Account, app_id, app_args=[], assets=[], accounts=[], apps=[]):
    print("---------- App calling -----------")
    txn_group = [transaction.ApplicationCallTxn(
        sender=addr.get_address(),
        sp=client.suggested_params(),
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=app_args,
        foreign_assets=assets,
        accounts=accounts,
        foreign_apps=apps,
    )]
    key = addr.get_private_key()
    return send(client, "Calling", [txn.sign(key) for txn in txn_group])


def create_asset(client: AlgodClient, sender: Account, unitname: str, decimals = 0):
    txn = transaction.AssetCreateTxn(
        sender=sender.get_address(),
        sp=client.suggested_params(),
        total=1_000_000,
        decimals=decimals,
        default_frozen=False,
        asset_name="asset",
        unit_name=unitname
    )
    signed_txn = txn.sign(sender.get_private_key())

    tx_id = client.send_transaction(signed_txn)

    response = wait_for_transaction(client, tx_id)

    assert response.asset_index is not None and response.asset_index > 0
    return response.asset_index


def compile_to_teal():
    # compile program to TEAL assembly
    with open("./approval.teal", "w") as f:
        x=approval_program()
        approval_program_teal = x
        f.write(approval_program_teal)

    # compile program to TEAL assembly
    with open("./clear.teal", "w") as f:
        clear_state_program_teal = clear_state_program()
        f.write(clear_state_program_teal)
    return approval_program_teal, clear_state_program_teal


def get_contracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    approval_program_teal, clear_state_program_teal = compile_to_teal()
    approval_program = fully_compile_contract(
        client, approval_program_teal)
    clear_state_program = fully_compile_contract(
        client, clear_state_program_teal)

    return approval_program, clear_state_program