from pyteal import *


def algo_delegate_authority_logic(app_id: int):
    """
    Signing authority for bidding app. This authority is responsible for receiving the ALGOs from the current bidder
    that owns the NFT, refunding the ALGOs to the previous owner of the NFT and after the bidding termination from this
    address we pay the ALGOs to the seller of the NFT.
    :param app_id: int - the application to which this delegate will be responsible for.
    :return:
    """

    is_bidding = Global.group_size() == Int(4)

    return If(is_bidding,
              And(Gtxn[0].application_id() == Int(app_id),
                  Gtxn[2].fee() <= Int(1000),
                  Gtxn[2].asset_close_to() == Global.zero_address(),
                  Gtxn[2].rekey_to() == Global.zero_address()),
              And(Gtxn[0].application_id() == Int(app_id),
                  Gtxn[1].fee() <= Int(1000),
                  Gtxn[1].asset_close_to() == Global.zero_address(),
                  Gtxn[1].rekey_to() == Global.zero_address()))
