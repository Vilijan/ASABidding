# Receive third title if you own both
# Transfer the donations to a smart contract
#  - If someone out bids you, your funds should be returned to you

from pyteal import *

from src.blockchain_utils import create_application, compile_program, execute_payment, change_asa_management, asa_opt_in
from algosdk.future import transaction as algo_txn
from src.credentials import get_client, main_developer_credentials, get_developer_credentials
from algosdk.logic import address as algo_addr


class AppVariables:
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
    titleOwner = "Silvio"
    highestBid = 0
    asaOwnerAddress = "737777777777777777777777777777777777777777777777777UFEJ2CI"


def application_start(initialization_code,
                      application_actions):
    is_app_initialization = Txn.application_id() == Int(0)
    are_actions_used = Txn.on_completion() == OnComplete.NoOp

    return If(is_app_initialization, initialization_code,
              If(are_actions_used, application_actions, Return(Int(0))))


def app_initialization_logic():
    return Seq([
        App.globalPut(Bytes(AppVariables.titleOwner), Bytes(DefaultValues.titleOwner)),
        App.globalPut(Bytes(AppVariables.highestBid), Int(DefaultValues.highestBid)),
        App.globalPut(Bytes(AppVariables.asaOwnerAddress), Addr(DefaultValues.asaOwnerAddress)),
        Return(Int(1))
    ])


def setup_possible_app_calls_logic(assets_delegate_code, transfer_asa_logic):
    """
    There are two possible options for executing the application actions:
    1. Setting up delegates
        - App call with two arguments: ASADelegateAddress and AlgoDelegateAddress
    2. Transferring the ASA
        - Atomic transfer with 4 transactions:
            2.1 - Application call with arguments new_owner_name: str
            2.2 - Payment to the algoDelegateAddress which represents the latest bid for the ASA.
            2.3 - Payment from the algoDelegateAddress to the old owner of the ASA which returns the algo funds.
            2.4 - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.
    :param assets_delegate_code:
    :param transfer_asa_logic:
    :return:
    """
    is_setting_up_delegates = Global.group_size() == Int(1)
    is_transferring_asa = Global.group_size() == Int(4)

    return If(is_setting_up_delegates, assets_delegate_code,
              If(is_transferring_asa, transfer_asa_logic, Return(Int(0))))


def setup_asset_delegates_logic():
    """
    Setting up delegates. Application call with two arguments
    1. ASADelegateAddress: str - the address of the smart contract that is responsible for delegating the ASA
    2. algoDelegateAddress: str - the address of the smart contract that is responsible for delegating the Algos
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
        3 - Payment from the algoDelegateAddress to the old owner of the ASA which returns the algo funds.
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


def clear_program():
    return Return(Int(1))


app_code = application_start(initialization_code=app_initialization_logic(),
                             application_actions=
                             setup_possible_app_calls_logic(assets_delegate_code=setup_asset_delegates_logic(),
                                                            transfer_asa_logic=asa_transfer_logic()))

# TODO: Save this code in .teal file
app_code_compiled = compileTeal(app_code, mode=Mode.Application, version=2)
clear_program_compiled = compileTeal(clear_program(), mode=Mode.Application, version=2)

main_dev_pk, main_dev_address = main_developer_credentials()
dev_pk, dev_address = get_developer_credentials(developer_id=1)
client = get_client()

# TODO: Every step should be a function
# 1. App creation


global_schema = algo_txn.StateSchema(num_uints=AppVariables.number_of_int(),
                                     num_byte_slices=AppVariables.number_of_str())
local_schema = algo_txn.StateSchema(num_uints=0,
                                    num_byte_slices=0)

approval_program_bytes = compile_program(client=client, source_code=app_code_compiled)
clear_program_bytes = compile_program(client=client, source_code=clear_program_compiled)

app_id = create_application(client=client,
                            creator_private_key=main_dev_pk,
                            approval_program=approval_program_bytes,
                            clear_program=clear_program_bytes,
                            global_schema=global_schema,
                            local_schema=local_schema,
                            app_args=None)

print(f'app_id:{app_id}')

# 2. Create ASA

from src.blockchain_utils import create_algorand_standard_asset

asa_id = create_algorand_standard_asset(client=client,
                                        creator_private_key=main_dev_pk,
                                        unit_name="wawa",
                                        asset_name="wawa",
                                        total=1,
                                        decimals=0,
                                        manager_address=main_dev_address,
                                        reserve_address=main_dev_address,
                                        freeze_address=main_dev_address,
                                        clawback_address=main_dev_address)

print(f'asa_id:{asa_id}')

# TODO: Remove this
# app_id = 16764560
# asa_id = 16764594

# 3. Setup ASA Delegate Smart Contract
from src.asa_delegate_authority import asa_delegate_authority_logic

asa_delegate_authority_logic_compiled = compileTeal(asa_delegate_authority_logic(app_id=app_id,
                                                                                 asa_id=asa_id),
                                                    mode=Mode.Signature,
                                                    version=2)

asa_delegate_authority_logic_bytes = compile_program(client=client, source_code=asa_delegate_authority_logic_compiled)

asa_delegate_authority_address = algo_addr(asa_delegate_authority_logic_bytes)

print(f'asa_delegate_authority_address:{asa_delegate_authority_address}')

# 4. Add some algos for fees to the ASA Delegate Smart Contract address

execute_payment(client=client,
                sender_private_key=main_dev_pk,
                reciever_address=asa_delegate_authority_address,
                amount=1000000)

# 5. Setup ASA credentials to the ASA Delegate Smart Contract address

change_asa_management(client=client,
                      current_manager_pk=main_dev_pk,
                      asa_id=asa_id,
                      manager_address="",
                      reserve_address=None,
                      freeze_address="",
                      clawback_address=asa_delegate_authority_address)

# 6. Setup Algo Delegate Smart Contract
from src.algo_delegate_authority import algo_delegate_authority_logic

algo_delegate_authority_logic_compiled = compileTeal(algo_delegate_authority_logic(app_id=app_id),
                                                     mode=Mode.Signature,
                                                     version=2)

algo_delegate_authority_logic_bytes = compile_program(client=client, source_code=algo_delegate_authority_logic_compiled)

algo_delegate_authority_address = algo_addr(algo_delegate_authority_logic_bytes)

print(f'algo_delegate_authority_address:{algo_delegate_authority_address}')

# 7. Add some algos for fees to the ASA Delegate Smart Contract address

execute_payment(client=client,
                sender_private_key=main_dev_pk,
                reciever_address=algo_delegate_authority_address,
                amount=1000000)

# 8. Setting up the delegates authorities in the app

from algosdk.encoding import decode_address
from src.blockchain_utils import call_application, get_default_suggested_params, wait_for_confirmation

app_args = [
    decode_address(asa_delegate_authority_address),
    decode_address(algo_delegate_authority_address)
]

call_application(client=client,
                 caller_private_key=main_dev_pk,
                 app_id=app_id,
                 on_comlete=algo_txn.OnComplete.NoOpOC,
                 app_args=app_args)

# # 9. Atomic transfer application call
# ------------------


# 9.1 Application tnx call
params = get_default_suggested_params(client=client)
new_owner_args = ["Vilijan"]

SENDER_ADDRESS = dev_address
SENDER_PK = dev_pk

application_call_txn = algo_txn.ApplicationCallTxn(sender=SENDER_ADDRESS,
                                                   sp=params,
                                                   index=app_id,
                                                   app_args=new_owner_args,
                                                   on_complete=algo_txn.OnComplete.NoOpOC)

# 9.2 Payment txn to algo delegate authority
biding_payment_txn = algo_txn.PaymentTxn(sender=SENDER_ADDRESS,
                                         sp=params,
                                         receiver=algo_delegate_authority_address,
                                         amt=5000)

# 9.3 Payment txn from algo delegate authority the old owner
OLD_AMOUNT = 0
OLD_OWNER = "737777777777777777777777777777777777777777777777777UFEJ2CI"

# OLD_AMOUNT = 3000
# OLD_OWNER = dev_address

algo_transfer_txn = algo_txn.PaymentTxn(sender=algo_delegate_authority_address,
                                        sp=params,
                                        receiver=OLD_OWNER,
                                        amt=OLD_AMOUNT)

# 9.4 Asset transfer txn from asa delegate authority to the new owner

asa_opt_in(client=client,
           sender_private_key=SENDER_PK,
           asa_id=asa_id)

asa_transfer_txn = algo_txn.AssetTransferTxn(sender=asa_delegate_authority_address,
                                             sp=params,
                                             receiver=SENDER_ADDRESS,
                                             amt=1,
                                             index=asa_id,
                                             revocation_target=main_dev_address)

#
# # Atomic transfer
#
gid = algo_txn.calculate_group_id([application_call_txn, biding_payment_txn, algo_transfer_txn, asa_transfer_txn])

application_call_txn.group = gid
biding_payment_txn.group = gid
algo_transfer_txn.group = gid
asa_transfer_txn.group = gid

application_call_txn_signed = application_call_txn.sign(SENDER_PK)
biding_payment_txn_signed = biding_payment_txn.sign(SENDER_PK)

return_payment_txn_logic_signature = algo_txn.LogicSig(algo_delegate_authority_logic_bytes)
return_payment_txn_signed = algo_txn.LogicSigTransaction(algo_transfer_txn, return_payment_txn_logic_signature)

asa_transfer_txn_logic_signature = algo_txn.LogicSig(asa_delegate_authority_logic_bytes)
asa_transfer_txn_signed = algo_txn.LogicSigTransaction(asa_transfer_txn, asa_transfer_txn_logic_signature)

signed_group = [application_call_txn_signed, biding_payment_txn_signed, return_payment_txn_signed,
                asa_transfer_txn_signed]

txid = client.send_transactions(signed_group)

print(txid)

wait_for_confirmation(client, txid)
