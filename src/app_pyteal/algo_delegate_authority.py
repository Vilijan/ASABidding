from pyteal import *


def algo_delegate_authority_logic(app_id: int):
    """
    Signing authority for bidding app. This authority is responsible for receiving the ALGOs from the current bidder
    that owns the NFT, while also refunding the ALGOs to the previous owner of the NFT.
    :param app_id: int - the application to which this delegate will be responsible for.
    :return:
    """
    is_calling_right_app = Gtxn[0].application_id() == Int(app_id)
    is_acceptable_fee = Gtxn[2].fee() <= Int(1000)
    is_valid_close_to_address = Gtxn[2].asset_close_to() == Global.zero_address()
    is_valid_rekey_to_address = Gtxn[2].rekey_to() == Global.zero_address()

    return And(is_calling_right_app,
               is_acceptable_fee,
               is_valid_close_to_address,
               is_valid_rekey_to_address)
