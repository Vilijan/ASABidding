# Receive third title if you own both
# Transfer the donations to a smart contract
#  - If someone out bids you, your funds should be returned to you

from pyteal import *


def application_start(initialization_code,
                      application_actions):
    is_app_initialization = Txn.application_id() == Int(0)
    are_actions_used = Txn.on_completion() == OnComplete.NoOp

    return If(is_app_initialization, initialization_code,
              If(are_actions_used, application_actions, Return(Int(0))))


def app_initialization_logic():
    return Seq([
        App.globalPut(Bytes("TitleOwner"), Bytes("wawa")),
        App.globalPut(Bytes("HighestBid"), Int(0)),
        App.globalPut(Bytes("OwnerAddress"), Addr("737777777777777777777777777777777777777777777777777UFEJ2CI")),
        Return(Int(1))
    ])


def setup_possible_app_calls_logic(signing_authority_code, transfer_title_logic):
    is_setting_up_signing_authority = Global.group_size() == Int(1)
    is_transferring_title = Global.group_size() == Int(3)

    return If(is_setting_up_signing_authority, signing_authority_code,
              If(is_transferring_title, transfer_title_logic, Return(Int(0))))


def setup_signing_authority_logic():
    signing_authority = App.globalGetEx(Int(0), Bytes("SigningAuthority"))

    setup_failed = Seq([
        Return(Int(0))
    ])

    setup_signing_authority = Seq([
        App.globalPut(Bytes("SigningAuthority"), Txn.application_args[0]),
        Return(Int(1))
    ])

    return Seq([
        signing_authority,
        If(signing_authority.hasValue(), setup_failed, setup_signing_authority)
    ])


def title_transfer_logic():
    # 1. Application call (new_owner: str)
    # 2. Payment to signing authority
    # 3. Payment from signing authority to old owner

    # Valid first transaction
    first_transaction_is_application_call = Gtxn[0].type_enum() == TxnType.ApplicationCall
    first_transaction_has_two_arguments = Gtxn[0].application_args.length() == Int(1)

    valid_first_transaction = And(first_transaction_is_application_call,
                                  first_transaction_has_two_arguments)

    # Valid second transaction
    second_transaction_is_payment = Gtxn[1].type_enum() == TxnType.Payment
    do_first_two_transaction_have_same_sender = Gtxn[1].sender() == Gtxn[0].sender()

    current_highest_bid = App.globalGet(Bytes("HighestBid"))
    is_valid_amount_to_change_titles = Gtxn[1].amount() > current_highest_bid

    signing_authority_address = App.globalGet(Bytes("SigningAuthority"))
    is_paid_to_signing_authority = Gtxn[1].receiver() == signing_authority_address

    valid_second_transaction = And(second_transaction_is_payment,
                                   do_first_two_transaction_have_same_sender,
                                   is_valid_amount_to_change_titles,
                                   is_paid_to_signing_authority)

    # Valid third transaction
    old_owner_address = App.globalGet(Bytes("OwnerAddress"))

    third_transaction_is_payment = Gtxn[2].type_enum() == TxnType.Payment
    is_paid_from_signing_authority = Gtxn[2].sender() == signing_authority_address
    is_paid_to_old_owner = Gtxn[2].receiver() == old_owner_address
    is_paid_right_amount = Gtxn[2].amount() == current_highest_bid

    valid_third_transaction = And(third_transaction_is_payment,
                                  is_paid_from_signing_authority,
                                  is_paid_to_old_owner,
                                  is_paid_right_amount)

    # Updating the app state
    update_owner_name = App.globalPut(Bytes("TitleOwner"), Gtxn[0].application_args[0])
    update_highest_bid = App.globalPut(Bytes("HighestBid"), Gtxn[1].amount())
    update_owner_address = App.globalPut(Bytes("OwnerAddress"), Gtxn[1].sender())
    update_app_state = Seq([
        update_highest_bid,
        update_owner_address,
        Return(Int(1))
    ])

    are_valid_transactions = And(valid_first_transaction,
                                 valid_second_transaction,
                                 valid_third_transaction)

    return If(are_valid_transactions, update_app_state, Seq([Return(Int(0))]))


def clear_program():
    return Return(Int(1))


app_code = application_start(initialization_code=app_initialization_logic(),
                             application_actions=
                             setup_possible_app_calls_logic(signing_authority_code=setup_signing_authority_logic(),
                                                            transfer_title_logic=title_transfer_logic()))

app_code_compiled = compileTeal(app_code, mode=Mode.Application, version=2)
clear_program_compiled = compileTeal(clear_program(), mode=Mode.Application, version=2)

from src.blockchain_utils import create_application, compile_program, execute_payment
from algosdk.future import transaction as algo_txn
from src.credentials import get_client, main_developer_credentials, get_developer_credentials

main_dev_pk, main_dev_address = main_developer_credentials()
dev_pk, dev_address = get_developer_credentials(developer_id=1)
client = get_client()

global_schema = algo_txn.StateSchema(num_uints=1,
                                     num_byte_slices=3)
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

print(app_id)

# Create smart contract logic
from src.new_features_signing_authority import signing_authority_logic
from algosdk.logic import address as algo_addr

# app_id = 16530657

signing_authority_code_compiled = compileTeal(signing_authority_logic(app_id=app_id),
                                              mode=Mode.Signature,
                                              version=2)

signing_authority_code_bytes = compile_program(client=client, source_code=signing_authority_code_compiled)

signing_authority_address = algo_addr(signing_authority_code_bytes)

print(signing_authority_address)

execute_payment(client=client,
                sender_private_key=main_dev_pk,
                reciever_address=signing_authority_address,
                amount=1000000)

from algosdk.encoding import decode_address
from src.blockchain_utils import call_application, get_default_suggested_params, wait_for_confirmation

# 1. Setting up application signing authority
original_address = decode_address(signing_authority_address)

app_args = [
    original_address
]

call_application(client=client,
                 caller_private_key=main_dev_pk,
                 app_id=app_id,
                 on_comlete=algo_txn.OnComplete.NoOpOC,
                 app_args=app_args)

# 2. Atomic transfer application call
# ------------------


# 2.1 Application call
params = get_default_suggested_params(client=client)
new_owner_args = ["1"]

application_call_txn = algo_txn.ApplicationCallTxn(sender=dev_address,
                                                   sp=params,
                                                   index=app_id,
                                                   app_args=new_owner_args,
                                                   on_complete=algo_txn.OnComplete.NoOpOC)

# 2.2 Payment
biding_payment_txn = algo_txn.PaymentTxn(sender=dev_address,
                                         sp=params,
                                         receiver=signing_authority_address,
                                         amt=6000)

# 2.3 Payment
# OLD_AMOUNT = 0
# OLD_OWNER = "737777777777777777777777777777777777777777777777777UFEJ2CI"

OLD_AMOUNT = 5000
OLD_OWNER = main_dev_address

return_payment_txn = algo_txn.PaymentTxn(sender=signing_authority_address,
                                         sp=params,
                                         receiver=OLD_OWNER,
                                         amt=OLD_AMOUNT)

# Atomic transfer

gid = algo_txn.calculate_group_id([application_call_txn, biding_payment_txn, return_payment_txn])

application_call_txn.group = gid
biding_payment_txn.group = gid
return_payment_txn.group = gid

claim_transaction_signed = application_call_txn.sign(dev_pk)
donation_transaction_signed = biding_payment_txn.sign(dev_pk)

signing_logic_signature = algo_txn.LogicSig(signing_authority_code_bytes)

crown_transfer_transaction_signed = algo_txn.LogicSigTransaction(return_payment_txn, signing_logic_signature)

signed_group = [claim_transaction_signed, donation_transaction_signed, crown_transfer_transaction_signed]
txid = client.send_transactions(signed_group)

print(txid)

wait_for_confirmation(client, txid)