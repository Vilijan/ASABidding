from pyteal import *


def transferring_titles_stateless_contract_logic(app_id: int,
                                                 donation_receiver: str,
                                                 crown_id: int,
                                                 sceptre_id: int):
    """
    Stateless smart contract that approves and transfers the appropriate ownership of the titles. This spending
    from the stateless contract is a third transaction of an atomic transfer with 3 transactions:
    1. Calls the AlgoRealm application
    2. Donates Algo to the reward pool
    3. Claims the corresponding title
    :return:
    """
    valid_group_size = Global.group_size() == Int(3)
    # 1
    is_application_call = Gtxn[0].type_enum() == TxnType.ApplicationCall
    is_calling_algorealm_app = Gtxn[0].application_id() == Int(app_id)

    # 2
    is_money_sending_call = Gtxn[1].type_enum() == TxnType.Payment
    is_the_same_sender = Gtxn[0].sender() == Gtxn[1].sender()
    is_the_pool_reciever = Gtxn[1].receiver() == Addr(address=donation_receiver)

    # 3
    is_transaction_transfer_call = Gtxn[2].type_enum() == TxnType.AssetTransfer
    is_the_valid_receiver = Gtxn[2].asset_receiver() == Gtxn[1].sender()

    is_crown_transferred = Gtxn[2].xfer_asset() == Int(crown_id)
    is_sceptre_transferred = Gtxn[2].xfer_asset() == Int(sceptre_id)
    is_valid_asset_transfer = Or(is_crown_transferred, is_sceptre_transferred)

    is_valid_asset_amount = Gtxn[2].asset_amount() == Int(1)
    is_acceptable_fee = Gtxn[2].fee() <= Int(1000)

    is_valid_close_to_address = Gtxn[2].asset_close_to() == Global.zero_address()
    is_valid_rekey_to_address = Gtxn[2].rekey_to() == Global.zero_address()

    return And(valid_group_size,
               is_application_call,
               is_calling_algorealm_app,
               is_money_sending_call,
               is_the_same_sender,
               is_the_pool_reciever,
               is_transaction_transfer_call,
               is_the_valid_receiver,
               is_valid_asset_transfer,
               is_valid_asset_amount,
               is_acceptable_fee,
               is_valid_close_to_address,
               is_valid_rekey_to_address)
