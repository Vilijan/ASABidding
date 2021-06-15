from pyteal import *


def signing_authority_logic(app_id: int):
    """
    Signing authority for bidding app. Signs a group transactions and returns money to the owner.
    :param app_id:
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
