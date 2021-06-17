from pyteal import *


def asa_delegate_authority_logic(app_id: int, asa_id: int):
    """
    :param app_id:
    :param asa_id:
    :return:
    """
    is_calling_right_app = Gtxn[0].application_id() == Int(app_id)
    is_valid_amount = Gtxn[3].asset_amount() == Int(1)
    is_valid_asa_transferred = Gtxn[3].xfer_asset() == Int(asa_id)
    is_acceptable_fee = Gtxn[3].fee() <= Int(1000)
    is_valid_close_to_address = Gtxn[3].asset_close_to() == Global.zero_address()
    is_valid_rekey_to_address = Gtxn[3].rekey_to() == Global.zero_address()

    return And(is_calling_right_app,
               is_valid_amount,
               is_valid_asa_transferred,
               is_acceptable_fee,
               is_valid_close_to_address,
               is_valid_rekey_to_address)
