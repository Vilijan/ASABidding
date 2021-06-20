from src.app_pyteal.app_source_code import approval_program, clear_program, AppVariables
from src.app_pyteal.asa_delegate_authority import asa_delegate_authority_logic
from src.app_pyteal.algo_delegate_authority import algo_delegate_authority_logic

import src.app_utils.blockchain_utils as blockchain_utils
import src.app_utils.credentials as developer_credentials

from pyteal import compileTeal, Mode

from algosdk import logic as algo_logic
from algosdk.future import transaction as algo_txn
from algosdk.encoding import decode_address


class AppInitializationService:

    def __init__(self,
                 app_creator_pk: str,
                 app_creator_address: str,
                 asa_unit_name: str,
                 asa_asset_name: str,
                 teal_version: int = 2):
        self.app_creator_pk = app_creator_pk
        self.app_creator_address = app_creator_address
        self.asa_unit_name = asa_unit_name
        self.asa_asset_name = asa_asset_name
        self.teal_version = teal_version

        self.client = developer_credentials.get_client()
        self.approval_program_code = approval_program()
        self.clear_program_code = clear_program()

        self.app_id = -1
        self.asa_id = -1
        self.asa_delegate_authority_address = ''
        self.algo_delegate_authority_address = ''

    def create_application(self):
        approval_program_compiled = compileTeal(self.approval_program_code,
                                                mode=Mode.Application,
                                                version=self.teal_version)
        clear_program_compiled = compileTeal(self.clear_program_code,
                                             mode=Mode.Application,
                                             version=self.teal_version)

        approval_program_bytes = blockchain_utils.compile_program(client=self.client,
                                                                  source_code=approval_program_compiled)

        clear_program_bytes = blockchain_utils.compile_program(client=self.client,
                                                               source_code=clear_program_compiled)

        global_schema = algo_txn.StateSchema(num_uints=AppVariables.number_of_int(),
                                             num_byte_slices=AppVariables.number_of_str())

        local_schema = algo_txn.StateSchema(num_uints=0,
                                            num_byte_slices=0)

        self.app_id = blockchain_utils.create_application(client=self.client,
                                                          creator_private_key=self.app_creator_pk,
                                                          approval_program=approval_program_bytes,
                                                          clear_program=clear_program_bytes,
                                                          global_schema=global_schema,
                                                          local_schema=local_schema,
                                                          app_args=None)

    def create_asa(self):
        self.asa_id = blockchain_utils.create_algorand_standard_asset(client=self.client,
                                                                      creator_private_key=self.app_creator_pk,
                                                                      unit_name=self.asa_unit_name,
                                                                      asset_name=self.asa_asset_name,
                                                                      total=1,
                                                                      decimals=0,
                                                                      manager_address=self.app_creator_address,
                                                                      reserve_address=self.app_creator_address,
                                                                      freeze_address=self.app_creator_address,
                                                                      clawback_address=self.app_creator_address,
                                                                      default_frozen=True)

    def setup_asa_delegate_smart_contract(self):
        if self.app_id == -1:
            raise ValueError('The application has not been created')
        if self.asa_id == -1:
            raise ValueError('The Algorand Standard Asset of interest has not been created')

        asa_delegate_authority_compiled = compileTeal(asa_delegate_authority_logic(app_id=self.app_id,
                                                                                   asa_id=self.asa_id),
                                                      mode=Mode.Signature,
                                                      version=self.teal_version)

        asa_delegate_authority_bytes = blockchain_utils.compile_program(client=self.client,
                                                                        source_code=asa_delegate_authority_compiled)

        self.asa_delegate_authority_address = algo_logic.address(asa_delegate_authority_bytes)

    def deposit_fee_funds_to_asa_delegate_authority(self):
        if self.asa_delegate_authority_address == '':
            raise ValueError('The asa delegate authority has not been created')

        blockchain_utils.execute_payment(client=self.client,
                                         sender_private_key=self.app_creator_pk,
                                         reciever_address=self.asa_delegate_authority_address,
                                         amount=1000000)

    def change_asa_credentials(self):
        if self.asa_id == -1:
            raise ValueError('The Algorand Standard Asset of interest has not been created')

        if self.asa_delegate_authority_address == '':
            raise ValueError('The asa delegate authority has not been created')

        blockchain_utils.change_asa_management(client=self.client,
                                               current_manager_pk=self.app_creator_pk,
                                               asa_id=self.asa_id,
                                               manager_address="",
                                               reserve_address=None,
                                               freeze_address="",
                                               clawback_address=self.asa_delegate_authority_address)

    def setup_algo_delegate_smart_contract(self):
        if self.app_id == -1:
            raise ValueError('The application has not been created')

        algo_delegate_authority_compiled = compileTeal(algo_delegate_authority_logic(app_id=self.app_id),
                                                       mode=Mode.Signature,
                                                       version=self.teal_version)

        algo_delegate_authority_bytes = blockchain_utils.compile_program(client=self.client,
                                                                         source_code=algo_delegate_authority_compiled)

        self.algo_delegate_authority_address = algo_logic.address(algo_delegate_authority_bytes)

    def deposit_fee_funds_to_algo_delegate_authority(self):
        if self.algo_delegate_authority_address == '':
            raise ValueError('The algo delegate authority has not been created')

        blockchain_utils.execute_payment(client=self.client,
                                         sender_private_key=self.app_creator_pk,
                                         reciever_address=self.algo_delegate_authority_address,
                                         amount=1000000)

    def setup_app_delegates_authorities(self):
        if self.app_id == -1:
            raise ValueError('The application has not been created')

        if self.asa_id == -1:
            raise ValueError('The Algorand Standard Asset of interest has not been created')

        if self.asa_delegate_authority_address == '':
            raise ValueError('The asa delegate authority has not been created')

        if self.algo_delegate_authority_address == '':
            raise ValueError('The algo delegate authority has not been created')

        app_args = [
            decode_address(self.asa_delegate_authority_address),
            decode_address(self.algo_delegate_authority_address),
            decode_address(self.app_creator_address)
        ]

        blockchain_utils.call_application(client=self.client,
                                          caller_private_key=self.app_creator_pk,
                                          app_id=self.app_id,
                                          on_comlete=algo_txn.OnComplete.NoOpOC,
                                          app_args=app_args)
