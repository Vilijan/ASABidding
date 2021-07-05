from src.app_services.app_initializaion_service import AppInitializationService
from src.app_services.app_interaction_service import AppInteractionService
from src.app_utils.credentials import main_developer_credentials, get_developer_credentials

main_dev_pk, main_dev_address = main_developer_credentials()

app_initialization_service = AppInitializationService(app_creator_pk=main_dev_pk,
                                                      app_creator_address=main_dev_address,
                                                      asa_unit_name="wawa",
                                                      asa_asset_name="wawa",
                                                      app_duration=150,
                                                      teal_version=3)

app_initialization_service.create_application()

app_initialization_service.create_asa()

app_initialization_service.setup_asa_delegate_smart_contract()
app_initialization_service.deposit_fee_funds_to_asa_delegate_authority()

app_initialization_service.change_asa_credentials()

app_initialization_service.setup_algo_delegate_smart_contract()
app_initialization_service.deposit_fee_funds_to_algo_delegate_authority()

app_initialization_service.setup_app_delegates_authorities()

print(f'app_id: {app_initialization_service.app_id} \n'
      f'asa_id: {app_initialization_service.asa_id} \n'
      f'asa_delegate_authority_address: {app_initialization_service.asa_delegate_authority_address} \n'
      f'algo_delegate_authority_address: {app_initialization_service.algo_delegate_authority_address}')

bidder_pk, bidder_address = get_developer_credentials(developer_id=1)

app_interaction_service = AppInteractionService(app_id=app_initialization_service.app_id,
                                                asa_id=app_initialization_service.asa_id,
                                                current_owner_address=main_dev_address,
                                                teal_version=3)

app_interaction_service.execute_bidding(bidder_private_key=bidder_pk,
                                        bidder_address=bidder_address,
                                        amount=3000000)

app_interaction_service.execute_bidding(bidder_private_key=main_dev_pk,
                                        bidder_address=main_dev_address,
                                        amount=5000000)

# This should fail if we try to submit it after the bidding process has ended
# app_interaction_service.execute_bidding(bidder_private_key=bidder_pk,
#                                         bidder_address=bidder_address,
#                                         amount=5000005)

app_interaction_service.pay_to_seller(asa_seller_address=app_initialization_service.app_creator_address)
