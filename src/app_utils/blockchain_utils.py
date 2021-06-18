import base64
from algosdk.v2client import algod
from algosdk.future import transaction as algo_txn
from typing import List, Any, Optional
from algosdk import account as algo_acc


def wait_for_confirmation(client, txid):
    """
    Utility function to wait until the transaction is
    confirmed before proceeding.
    """
    last_round = client.status().get('last-round')
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get('confirmed-round') and txinfo.get('confirmed-round') > 0):
        print("Waiting for confirmation")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print("Transaction {} confirmed in round {}.".format(
        txid, txinfo.get('confirmed-round')))
    return txinfo


def compile_program(client: algod.AlgodClient, source_code):
    """
    :param client: algorand client
    :param source_code: teal source code
    :return:
        Decoded byte program
    """
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])


def get_default_suggested_params(client: algod.AlgodClient):
    """
    Gets default suggested params with flat transaction fee and fee amount of 1000.
    :param client:
    :return:
    """
    suggested_params = client.suggested_params()

    suggested_params.flat_fee = True
    suggested_params.fee = 1000

    return suggested_params


def create_application(client: algod.AlgodClient,
                       creator_private_key: str,
                       approval_program: bytes,
                       clear_program: bytes,
                       global_schema: algo_txn.StateSchema,
                       local_schema: algo_txn.StateSchema,
                       app_args: Optional[List[Any]]) -> Optional[int]:
    """
    :param client: algorand client
    :param creator_private_key: private key of the creator of the application
    :param approval_program: encoded source code in bytes for the approval program
    :param clear_program: encoded source code in bytes for the clear program
    :param global_schema: global schema for the application
    :param local_schema: local schema for the application
    :param app_args: list of arguments for the application
    :return:
        str: If the creation is successful the app's id is returned.
    """
    creator_address = algo_acc.address_from_private_key(private_key=creator_private_key)
    suggested_params = get_default_suggested_params(client=client)

    txn = algo_txn.ApplicationCreateTxn(sender=creator_address,
                                        sp=suggested_params,
                                        on_complete=algo_txn.OnComplete.NoOpOC.real,
                                        approval_program=approval_program,
                                        clear_program=clear_program,
                                        global_schema=global_schema,
                                        local_schema=local_schema,
                                        app_args=app_args)

    signed_txn = txn.sign(private_key=creator_private_key)
    tx_id = signed_txn.transaction.get_txid()

    client.send_transaction(signed_txn)

    wait_for_confirmation(client, tx_id)

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']

    return app_id


def call_application(client: algod.AlgodClient,
                     caller_private_key: str,
                     app_id: int,
                     on_comlete: algo_txn.OnComplete,
                     app_args: Optional[List[Any]] = None) -> Optional[str]:
    """
    Calls an application.
    :param client:
    :param caller_private_key:
    :param app_id:
    :param on_comlete:
    :param app_args:
    :return:
    """

    caller_address = algo_acc.address_from_private_key(private_key=caller_private_key)
    suggested_params = get_default_suggested_params(client=client)

    txn = algo_txn.ApplicationCallTxn(sender=caller_address,
                                      sp=suggested_params,
                                      index=app_id,
                                      app_args=app_args,
                                      on_complete=on_comlete)

    txn_signed = txn.sign(private_key=caller_private_key)
    tx_id = txn_signed.transaction.get_txid()

    client.send_transaction(txn_signed)

    wait_for_confirmation(client, tx_id)

    return tx_id


def create_algorand_standard_asset(client: algod.AlgodClient,
                                   creator_private_key: str,
                                   unit_name: str,
                                   asset_name: str,
                                   total: int,
                                   decimals: int,
                                   manager_address: Optional[str] = None,
                                   reserve_address: Optional[str] = None,
                                   freeze_address: Optional[str] = None,
                                   clawback_address: Optional[str] = None,
                                   url: Optional[str] = None,
                                   default_frozen: bool = False) -> Optional[int]:
    """

    :param client: Algo client
    :param creator_private_key: creators private key.
    :param unit_name: unit name of the ASA
    :param asset_name: name of the ASA
    :param total: total number of ASA
    :param decimals: number of decimals for the ASA
    :param manager_address:
    :param reserve_address:
    :param freeze_address:
    :param clawback_address:
    :param url:
    :param default_frozen:
    :return:
        If the ASA is successfully created the ASA's id is returned.
    """
    suggested_params = get_default_suggested_params(client=client)

    creator_address = algo_acc.address_from_private_key(private_key=creator_private_key)

    txn = algo_txn.AssetConfigTxn(sender=creator_address,
                                  sp=suggested_params,
                                  total=total,
                                  default_frozen=default_frozen,
                                  unit_name=unit_name,
                                  asset_name=asset_name,
                                  manager=manager_address,
                                  reserve=reserve_address,
                                  freeze=freeze_address,
                                  clawback=clawback_address,
                                  url=url,
                                  decimals=decimals)

    txn_signed = txn.sign(private_key=creator_private_key)

    txid = client.send_transaction(txn_signed)

    # Wait for the transaction to be confirmed
    wait_for_confirmation(client, txid)

    try:
        ptx = client.pending_transaction_info(txid)
        asset_id = ptx["asset-index"]
        return asset_id
    except Exception as e:
        print(e)
        return None


def asa_opt_in(client: algod.AlgodClient,
               sender_private_key: str,
               asa_id: int) -> Optional[str]:
    """
    Opts in to a algorand standard asset.
    :param client:
    :param sender_private_key:
    :param asa_id:
    :return:
    """
    suggested_params = get_default_suggested_params(client=client)
    sender_address = algo_acc.address_from_private_key(sender_private_key)

    txn = algo_txn.AssetTransferTxn(sender=sender_address,
                                    sp=suggested_params,
                                    receiver=sender_address,
                                    amt=0,
                                    index=asa_id)

    txn_signed = txn.sign(sender_private_key)
    txid = client.send_transaction(txn_signed)

    wait_for_confirmation(client=client, txid=txid)

    return txid


def change_asa_management(client: algod.AlgodClient,
                          current_manager_pk: str,
                          asa_id: int,
                          manager_address: Optional[str] = None,
                          reserve_address: Optional[str] = None,
                          freeze_address: Optional[str] = None,
                          clawback_address: Optional[str] = None):
    params = get_default_suggested_params(client=client)

    current_manager_address = algo_acc.address_from_private_key(private_key=current_manager_pk)

    txn = algo_txn.AssetConfigTxn(
        sender=current_manager_address,
        sp=params,
        index=asa_id,
        manager=manager_address,
        reserve=reserve_address,
        freeze=freeze_address,
        clawback=clawback_address,
        strict_empty_address_check=False)

    # sign by the current manager - Account 2
    stxn = txn.sign(current_manager_pk)
    txid = client.send_transaction(stxn)

    wait_for_confirmation(client=client, txid=txid)


def execute_payment(client: algod.AlgodClient,
                    sender_private_key: str,
                    reciever_address: str,
                    amount: int) -> Optional[str]:
    """
    Creates and executes a payment transaction
    :param client: Algorand client
    :param sender_private_key: sender's private key
    :param reciever_address: receiver's address
    :param amount: amount in micro algos
    :return: transaction id.
    """
    suggested_params = get_default_suggested_params(client=client)

    sender_address = algo_acc.address_from_private_key(private_key=sender_private_key)

    txn = algo_txn.PaymentTxn(sender=sender_address,
                              sp=suggested_params,
                              receiver=reciever_address,
                              amt=amount)

    txn_signed = txn.sign(sender_private_key)

    txid = client.send_transaction(txn_signed)

    wait_for_confirmation(client, txid)

    return txid
