from pyteal import *


class AppVariables:
    """
    All the possible global variables in the application.
    """
    asaSellerAddress = "asaSellerAddress"
    highestBid = "HighestBid"
    asaOwnerAddress = "ASAOwnerAddress"
    asaDelegateAddress = "ASADelegateAddress"
    algoDelegateAddress = "AlgoDelegateAddress"
    appStartRound = "appStartRound"
    appEndRound = "appEndRound"

    @classmethod
    def number_of_int(cls):
        return 3

    @classmethod
    def number_of_str(cls):
        return 4


class DefaultValues:
    """
    The default values for the global variables initialized on the transaction that creates the application.
    """
    highestBid = 0


def application_start(initialization_code,
                      application_actions):
    """
    Possible states of the application when it is started.
    :param initialization_code: This code will only run when the transaction that is creating the application is
    submitted on the network.
    :param application_actions: This code represents all the possible actions in the application.
    :return:
    """
    is_app_initialization = Txn.application_id() == Int(0)
    are_actions_used = Txn.on_completion() == OnComplete.NoOp

    return If(is_app_initialization, initialization_code,
              If(are_actions_used, application_actions, Return(Int(0))))


def app_initialization_logic():
    """
    Initialization of the global variables in the application with the previously defined default values. We only add
    a default name of the title owner and the highest bid which at the beginning is 0.
    :return:
    """
    return Seq([
        App.globalPut(Bytes(AppVariables.highestBid), Int(DefaultValues.highestBid)),
        App.globalPut(Bytes(AppVariables.appStartRound), Global.round()),
        Return(Int(1))
    ])


def setup_possible_app_calls_logic(asset_authorities_code, transfer_asa_code, payment_to_seller_code):
    """
    There are 3 possible options for executing the application actions:
    1. Setting up authorities
        - App call with 5 arguments: ASADelegateAddress, AlgoDelegateAddress, asaOwnerAddress, appDuration
        and ASASellerAddress.
    2. Transferring the ASA
        - Atomic transfer with 4 transactions:
            2.1 - Application call.
            2.2 - Payment to the algoDelegateAddress which represents the latest bid for the ASA.
            2.3 - Payment from the algoDelegateAddress to the old owner of the ASA which returns the algo funds.
            2.4 - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.
    3. Paying the highest bid to the asaSellerAddress. This can happen after the bidding period has ended.
        - Atomic transfer with 2 transactions:
            3.1 - Application call
            3.2 - Payment from the ALGO Delegate Authority to the asaSellerAddress.
    :param asset_authorities_code: The code that is responsible for setting up the delegate authorities in the app.
    :param transfer_asa_code: The code that is responsible for the bidding logic.
    :param payment_to_seller_code: The code that is responsible for paying the highest bid to the seller of the ASA.
    :return:
    """
    is_setting_up_asset_authorities = Global.group_size() == Int(1)
    is_transferring_asa = Global.group_size() == Int(4)
    is_payment_to_seller = Global.group_size() == Int(2)

    return If(is_setting_up_asset_authorities, asset_authorities_code,
              If(is_transferring_asa, transfer_asa_code,
                 If(is_payment_to_seller, payment_to_seller_code, Return(Int(0)))))


def setup_asset_authorities_logic():
    """
    Setting up delegates, first asset owner and the app duration. The setup of the authorities can be performed only once.
    If we try to modify them once they have been saved the application code should result with failure.
    This application call receives 5 arguments:
    1. ASADelegateAddress: str - the address of the smart contract that is responsible for delegating the ASA
    2. AlgoDelegateAddress: str - the address of the smart contract that is responsible for delegating the Algos
    3. asaOwnerAddress: str - the address of the first owner of the NFT.
    4. appDuration: int - the number of Rounds that the application will be available on the Network. The last round is
    calculated as: appStartRound + appDuration.
    5. asaSellerAddress: str - the address of the seller of the ASA. This address will receive the ALGOs funds from the
    highest bid once the bidding duration has ended.
    :return:
    """
    asa_delegate_authority = App.globalGetEx(Int(0), Bytes(AppVariables.asaDelegateAddress))
    algo_delegate_authority = App.globalGetEx(Int(0), Bytes(AppVariables.algoDelegateAddress))

    setup_failed = Seq([
        Return(Int(0))
    ])

    start_round = App.globalGet(Bytes(AppVariables.appStartRound))

    setup_authorities = Seq([
        App.globalPut(Bytes(AppVariables.asaDelegateAddress), Txn.application_args[0]),
        App.globalPut(Bytes(AppVariables.algoDelegateAddress), Txn.application_args[1]),
        App.globalPut(Bytes(AppVariables.asaOwnerAddress), Txn.application_args[2]),
        App.globalPut(Bytes(AppVariables.appEndRound), Add(start_round, Btoi(Txn.application_args[3]))),
        App.globalPut(Bytes(AppVariables.asaSellerAddress), Txn.application_args[4]),
        Return(Int(1))
    ])

    return Seq([
        asa_delegate_authority,
        algo_delegate_authority,
        If(Or(asa_delegate_authority.hasValue(), algo_delegate_authority.hasValue()), setup_failed, setup_authorities)
    ])


def asa_transfer_logic():
    """
    Transferring the ASA is atomic transfer with 4 transactions:
        1 - Application call.
        2 - Payment to the algoDelegateAddress which represents the latest bid for the ASA.
        3 - Payment from the algoDelegateAddress to the old owner of the ASA which returns the ALGO funds.
        4 - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.
    :return:
    """
    # Valid first transaction
    valid_first_transaction = Gtxn[0].type_enum() == TxnType.ApplicationCall

    # Valid second transaction
    second_transaction_is_payment = Gtxn[1].type_enum() == TxnType.Payment
    do_first_two_transaction_have_same_sender = Gtxn[1].sender() == Gtxn[0].sender()

    current_highest_bid = App.globalGet(Bytes(AppVariables.highestBid))
    is_valid_amount_to_change_titles = Gtxn[1].amount() > current_highest_bid

    algo_delegate_address = App.globalGet(Bytes(AppVariables.algoDelegateAddress))
    is_paid_to_algo_delegate_address = Gtxn[1].receiver() == algo_delegate_address

    valid_second_transaction = And(second_transaction_is_payment,
                                   do_first_two_transaction_have_same_sender,
                                   is_valid_amount_to_change_titles,
                                   is_paid_to_algo_delegate_address)

    # Valid third transaction
    old_owner_address = App.globalGet(Bytes(AppVariables.asaOwnerAddress))

    third_transaction_is_payment = Gtxn[2].type_enum() == TxnType.Payment
    is_paid_from_algo_delegate_authority = Gtxn[2].sender() == algo_delegate_address
    is_paid_to_old_owner = Gtxn[2].receiver() == old_owner_address
    is_paid_right_amount = Gtxn[2].amount() == current_highest_bid

    valid_third_transaction = And(third_transaction_is_payment,
                                  is_paid_from_algo_delegate_authority,
                                  is_paid_to_old_owner,
                                  is_paid_right_amount)

    # Valid fourth transaction
    asa_delegate_address = App.globalGet(Bytes(AppVariables.asaDelegateAddress))

    fourth_transaction_is_asset_transfer = Gtxn[3].type_enum() == TxnType.AssetTransfer
    is_paid_from_asa_delegate_authority = Gtxn[3].sender() == asa_delegate_address
    is_the_new_owner_receiving_the_asa = Gtxn[3].asset_receiver() == Gtxn[1].sender()

    valid_forth_transaction = And(fourth_transaction_is_asset_transfer,
                                  is_paid_from_asa_delegate_authority,
                                  is_the_new_owner_receiving_the_asa)

    # Valid time
    end_round = App.globalGet(Bytes(AppVariables.appEndRound))
    is_app_active = Global.round() <= end_round

    # Updating the app state
    update_highest_bid = App.globalPut(Bytes(AppVariables.highestBid), Gtxn[1].amount())
    update_owner_address = App.globalPut(Bytes(AppVariables.asaOwnerAddress), Gtxn[1].sender())
    update_app_state = Seq([
        update_highest_bid,
        update_owner_address,
        Return(Int(1))
    ])

    are_valid_transactions = And(valid_first_transaction,
                                 valid_second_transaction,
                                 valid_third_transaction,
                                 valid_forth_transaction,
                                 is_app_active)

    return If(are_valid_transactions, update_app_state, Seq([Return(Int(0))]))


def payment_to_seller_logic():
    """
    Once the bidding process has ended we should transfer the amount of highest bid of the ALGOs to the asaSellerAddress
    This is an atomic transfer of 2 transactions:
    1. Application call - where we make sure that the bidding duration of the app has ended.
    2. Payment transaction - this transaction represents the payment from the ALGO Delegate Authority to the
    asaSellerAddress. We need to make sure that the right amount of ALGOs is sent from the ALGO Delegate Authority
    to the asaOwnerAddress.
    :return:
    """
    # Valid first transaction
    end_round = App.globalGet(Bytes(AppVariables.appEndRound))
    is_application_call = Gtxn[0].type_enum() == TxnType.ApplicationCall
    bidding_period_has_ended = Global.round() > end_round

    valid_first_transaction = And(is_application_call, bidding_period_has_ended)

    # Valid second transaction
    is_payment_call = Gtxn[1].type_enum() == TxnType.Payment

    asa_seller_address = App.globalGet(Bytes(AppVariables.asaSellerAddress))
    valid_receiver_of_algos = asa_seller_address == Gtxn[1].receiver()

    highest_bid = App.globalGet(Bytes(AppVariables.highestBid))
    valid_amount_of_algos = highest_bid == Gtxn[1].amount()

    algo_delegate_authority = App.globalGet(Bytes(AppVariables.algoDelegateAddress))
    valid_sender = algo_delegate_authority == Gtxn[1].sender()

    valid_second_transaction = And(is_payment_call,
                                   valid_receiver_of_algos,
                                   valid_amount_of_algos,
                                   valid_sender)

    are_valid_transactions = And(valid_first_transaction,
                                 valid_second_transaction)

    return If(are_valid_transactions, Seq([Return(Int(1))]), Seq([Return(Int(0))]))


def approval_program():
    """
    Approval program of the application. Combines all the logic of the application that was implemented previously.
    :return:
    """
    return application_start(initialization_code=app_initialization_logic(),
                             application_actions=
                             setup_possible_app_calls_logic(asset_authorities_code=setup_asset_authorities_logic(),
                                                            transfer_asa_code=asa_transfer_logic(),
                                                            payment_to_seller_code=payment_to_seller_logic()))


def clear_program():
    """
    Clear program of the application. Always approves.
    :return:
    """
    return Return(Int(1))
