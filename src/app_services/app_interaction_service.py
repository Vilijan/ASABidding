from src.app_pyteal.app_source_code import DefaultValues
from src.app_pyteal.asa_delegate_authority import asa_delegate_authority_logic
from src.app_pyteal.algo_delegate_authority import algo_delegate_authority_logic

import src.app_utils.blockchain_utils as blockchain_utils
import src.app_utils.credentials as developer_credentials

from pyteal import compileTeal, Mode

from algosdk import logic as algo_logic
from algosdk.future import transaction as algo_txn


class AppInteractionService:

    def __init__(self,
                 app_id: int,
                 asa_id: int,
                 current_owner_address: str,
                 current_highest_bid: int = DefaultValues.highestBid,
                 teal_version: int = 2):
        self.client = developer_credentials.get_client()
        self.app_id = app_id
        self.asa_id = asa_id
        self.current_owner_address = current_owner_address
        self.current_highest_bid = current_highest_bid
        self.teal_version = teal_version

        asa_delegate_authority_compiled = compileTeal(asa_delegate_authority_logic(app_id=self.app_id,
                                                                                   asa_id=self.asa_id),
                                                      mode=Mode.Signature,
                                                      version=self.teal_version)

        self.asa_delegate_authority_code_bytes = \
            blockchain_utils.compile_program(client=self.client,
                                             source_code=asa_delegate_authority_compiled)

        self.asa_delegate_authority_address = algo_logic.address(self.asa_delegate_authority_code_bytes)

        algo_delegate_authority_compiled = compileTeal(algo_delegate_authority_logic(app_id=self.app_id),
                                                       mode=Mode.Signature,
                                                       version=self.teal_version)

        self.algo_delegate_authority_code_bytes = \
            blockchain_utils.compile_program(client=self.client,
                                             source_code=algo_delegate_authority_compiled)

        self.algo_delegate_authority_address = algo_logic.address(self.algo_delegate_authority_code_bytes)

    def execute_bidding(self,
                        bidder_name: str,
                        bidder_private_key: str,
                        bidder_address: str,
                        amount: int):
        params = blockchain_utils.get_default_suggested_params(client=self.client)

        # 1. Application call txn
        bidding_app_call_txn = algo_txn.ApplicationCallTxn(sender=bidder_address,
                                                           sp=params,
                                                           index=self.app_id,
                                                           app_args=[bidder_name],
                                                           on_complete=algo_txn.OnComplete.NoOpOC)

        # 2. Bidding payment transaction
        biding_payment_txn = algo_txn.PaymentTxn(sender=bidder_address,
                                                 sp=params,
                                                 receiver=self.algo_delegate_authority_address,
                                                 amt=amount)

        # 3. Payment txn from algo delegate authority the current owner
        algo_refund_txn = algo_txn.PaymentTxn(sender=self.algo_delegate_authority_address,
                                              sp=params,
                                              receiver=self.current_owner_address,
                                              amt=self.current_highest_bid)

        # 4. Asa opt-in for the bidder & asset transfer transaction
        blockchain_utils.asa_opt_in(client=self.client,
                                    sender_private_key=bidder_private_key,
                                    asa_id=self.asa_id)

        asa_transfer_txn = algo_txn.AssetTransferTxn(sender=self.asa_delegate_authority_address,
                                                     sp=params,
                                                     receiver=bidder_address,
                                                     amt=1,
                                                     index=self.asa_id,
                                                     revocation_target=self.current_owner_address)

        # Atomic transfer
        gid = algo_txn.calculate_group_id([bidding_app_call_txn,
                                           biding_payment_txn,
                                           algo_refund_txn,
                                           asa_transfer_txn])

        bidding_app_call_txn.group = gid
        biding_payment_txn.group = gid
        algo_refund_txn.group = gid
        asa_transfer_txn.group = gid

        bidding_app_call_txn_signed = bidding_app_call_txn.sign(bidder_private_key)
        biding_payment_txn_signed = biding_payment_txn.sign(bidder_private_key)

        algo_refund_txn_logic_signature = algo_txn.LogicSig(self.algo_delegate_authority_code_bytes)
        algo_refund_txn_signed = algo_txn.LogicSigTransaction(algo_refund_txn, algo_refund_txn_logic_signature)

        asa_transfer_txn_logic_signature = algo_txn.LogicSig(self.asa_delegate_authority_code_bytes)
        asa_transfer_txn_signed = algo_txn.LogicSigTransaction(asa_transfer_txn, asa_transfer_txn_logic_signature)

        signed_group = [bidding_app_call_txn_signed,
                        biding_payment_txn_signed,
                        algo_refund_txn_signed,
                        asa_transfer_txn_signed]

        txid = self.client.send_transactions(signed_group)

        blockchain_utils.wait_for_confirmation(self.client, txid)

        self.current_owner_address = bidder_address
        self.current_highest_bid = amount
