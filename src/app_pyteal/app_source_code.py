from pyteal import *


class AppVariables:
    """
    All the possible global variables in the application.
    """
    titleOwner = "TitleOwner"
    highestBid = "HighestBid"
    asaOwnerAddress = "OwnerAddress"
    asaDelegateAddress = "ASADelegateAddress"
    algoDelegateAddress = "AlgoDelegateAddress"

    @classmethod
    def number_of_int(cls):
        return 1

    @classmethod
    def number_of_str(cls):
        return 4


class DefaultValues:
    """
    The default values for the global variables initialized on the transaction that creates the application.
    """
    titleOwner = "Silvio"
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
        App.globalPut(Bytes(AppVariables.titleOwner), Bytes(DefaultValues.titleOwner)),
        App.globalPut(Bytes(AppVariables.highestBid), Int(DefaultValues.highestBid)),
        Return(Int(1))
    ])


def setup_possible_app_calls_logic(assets_delegate_code, transfer_asa_logic):
    """
    There are two possible options for executing the application actions:
    1. Setting up delegates
        - App call with 3 arguments: ASADelegateAddress, AlgoDelegateAddress and asaOwnerAddress.
    2. Transferring the ASA
        - Atomic transfer with 4 transactions:
            2.1 - Application call with arguments new_owner_name: str
            2.2 - Payment to the algoDelegateAddress which represents the latest bid for the ASA.
            2.3 - Payment from the algoDelegateAddress to the old owner of the ASA which returns the algo funds.
            2.4 - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.
    :param assets_delegate_code: The code that is responsible for setting up the delegate authorities in the app.
    :param transfer_asa_logic: The code that is responsible for the bidding logic.
    :return:
    """
    is_setting_up_delegates = Global.group_size() == Int(1)
    is_transferring_asa = Global.group_size() == Int(4)

    return If(is_setting_up_delegates, assets_delegate_code,
              If(is_transferring_asa, transfer_asa_logic, Return(Int(0))))


def setup_asset_delegates_logic():
    """
    Setting up delegates and the first asset owner. The setup of the authorities can be performed only once. If we try
    to modify them once they are saved the application code should result with failure. This application call receives
    3 arguments:
    1. ASADelegateAddress: str - the address of the smart contract that is responsible for delegating the ASA
    2. AlgoDelegateAddress: str - the address of the smart contract that is responsible for delegating the Algos
    3. asaOwnerAddress: str - the address of the first owner of the NFT.
    :return:
    """
    asa_delegate_authority = App.globalGetEx(Int(0), Bytes(AppVariables.asaDelegateAddress))
    algo_delegate_authority = App.globalGetEx(Int(0), Bytes(AppVariables.algoDelegateAddress))

    setup_failed = Seq([
        Return(Int(0))
    ])

    setup_delegates = Seq([
        App.globalPut(Bytes(AppVariables.asaDelegateAddress), Txn.application_args[0]),
        App.globalPut(Bytes(AppVariables.algoDelegateAddress), Txn.application_args[1]),
        App.globalPut(Bytes(AppVariables.asaOwnerAddress), Txn.application_args[2]),
        Return(Int(1))
    ])

    return Seq([
        asa_delegate_authority,
        algo_delegate_authority,
        If(Or(asa_delegate_authority.hasValue(), algo_delegate_authority.hasValue()), setup_failed, setup_delegates)
    ])


def asa_transfer_logic():
    """
    Transferring the ASA is atomic transfer with 4 transactions:
        1 - Application call with arguments new_owner_name: str
        2 - Payment to the algoDelegateAddress which represents the latest bid for the ASA.
        3 - Payment from the algoDelegateAddress to the old owner of the ASA which returns the ALGO funds.
        4 - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.
    :return:
    """
    # Valid first transaction
    first_transaction_is_application_call = Gtxn[0].type_enum() == TxnType.ApplicationCall
    first_transaction_has_one_argument = Gtxn[0].application_args.length() == Int(1)

    valid_first_transaction = And(first_transaction_is_application_call,
                                  first_transaction_has_one_argument)

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

    # Updating the app state
    update_owner_name = App.globalPut(Bytes(AppVariables.titleOwner), Gtxn[0].application_args[0])
    update_highest_bid = App.globalPut(Bytes(AppVariables.highestBid), Gtxn[1].amount())
    update_owner_address = App.globalPut(Bytes(AppVariables.asaOwnerAddress), Gtxn[1].sender())
    update_app_state = Seq([
        update_owner_name,
        update_highest_bid,
        update_owner_address,
        Return(Int(1))
    ])

    are_valid_transactions = And(valid_first_transaction,
                                 valid_second_transaction,
                                 valid_third_transaction,
                                 valid_forth_transaction)

    return If(are_valid_transactions, update_app_state, Seq([Return(Int(0))]))


def approval_program():
    """
    Approval program of the application. Combines all the logic of the application that was implemented previously.
    :return:
    """
    return application_start(initialization_code=app_initialization_logic(),
                             application_actions=
                             setup_possible_app_calls_logic(assets_delegate_code=setup_asset_delegates_logic(),
                                                            transfer_asa_logic=asa_transfer_logic()))


def clear_program():
    """
    Clear program of the application. Always approves.
    :return:
    """
    return Return(Int(1))
