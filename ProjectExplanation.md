# Algorand Standard Asset bidding application

## Overview

Through this solution I want to explain a system developed on the Algorand network that does automated transfer of an asset of interest to the person who has paid the most for that particular asset. 

Lets imagine a scenario in the today's world where an entity wants to sell some arbitrary asset for the highest possible price. The process of bidding for the asset and the process of transferring the ownership of the asset involves a lot of 3rd parties which adds a lot of additional costs to the process and adds the need to trust unknown institutions who operate behind the scenes. In this blog post I describe a system that tries to replace the 3rd party institutions with a code which is best described as a Smart Contract. 

We currently relay on a lot of signatures from well established institutions in order verify some processes. What if those signatures can be provided by compiling a deterministic program which is transparent and provides equal opportunity for everyone participating in the process ? 


## Application Usage

The decentralized application described in this solution has a goal to do automated bidding for a predefined Algorand Standard Asset (ASA). The usage process of the application is the following:

1. Some entity creates an ASA that want to sell on the Algorand blockchain network. This ASA can be mapped to anything in the physical world.
2. Users i.e. bidders who want to buy this ASA will call the application with the specified amount of ALGOs they want to pay.

   - If the current bidder has provided the highest amount of ALGOs the ASA will be automatically transferred to the bidder's wallet. The person who previously held the ASA will get refund for his ALGOs because he is no longer the highest bidder.

   - If the current bidder has provided lower amount of ALGOs than the current highest bidder the application will reject this transaction

The application is developed using [PyTeal](https://pyteal.readthedocs.io/en/latest/overview.html) which enables writing [Algorand Smart Contracts(ASC1)](https://developer.algorand.org/docs/features/asc1/) and the [py-algorand-sdk](https://github.com/algorand/py-algorand-sdk) that enables interactions with the Algorand network. You can find the source code for the application in the following [repository](https://github.com/Vilijan/ASABidding)

After completing this tutorial you will be able to initialize the application and interact with it with the following code:

```python
app_initialization_service = AppInitializationService(app_creator_pk=main_dev_pk,
                                                      app_creator_address=main_dev_address,
                                                      asa_unit_name="Apartment",
                                                      asa_asset_name="1204HS",
                                                      teal_version=3)

app_initialization_service.create_application()

app_initialization_service.create_asa()

app_initialization_service.setup_asa_delegate_smart_contract()
app_initialization_service.deposit_fee_funds_to_asa_delegate_authority()

app_initialization_service.change_asa_credentials()

app_initialization_service.setup_algo_delegate_smart_contract()
app_initialization_service.deposit_fee_funds_to_algo_delegate_authority()

app_initialization_service.setup_app_delegates_authorities()
```

```python
app_interaction_service = AppInteractionService(app_id=app_initialization_service.app_id,
                                                asa_id=app_initialization_service.asa_id,
                                                current_owner_address=main_dev_address,
                                                teal_version=3)

app_interaction_service.execute_bidding(bidder_name="Bob",
                                        bidder_private_key=bidder_pk,
                                        bidder_address=bidder_address,
                                        amount=3000)

app_interaction_service.execute_bidding(bidder_name="Alice",
                                        bidder_private_key=main_dev_pk,
                                        bidder_address=main_dev_address,
                                        amount=4000)
```

## Application architecture

The code of the ASA bidding application is well structured and separated in 3 main components:

1. **PyTeal** - this component contains all of the PyTeal code that is used in the application. The PyTeal code is later on divided into additional 3 sub-components:
   - *App Source Code* - This module defines all of the source code for the [Stateful Smart Contract](https://developer.algorand.org/docs/features/asc1/stateful/) that defines the logic of the application that manages the state of the application and handles the logic for determining the owner of the ASA. In the end in this module we have a function that provides to us the [TEAL](https://developer.algorand.org/docs/features/asc1/teal/) code for the approval and the clear program.
   - *ASA Delegate Authority* - This module defines the source code for the [Stateless Smart Contract](https://developer.algorand.org/docs/features/asc1/stateless/) that is responsible for transferring the ASA to the rightful owner. This contract acts as an authority that provides the signature which guarantees that the ASA is transferred to the correct owner. 
   - *ALGO Delegate Authority* - This module defines the source code for the Stateless Smart Contract that is responsible for refunding the ALGOs to the previous owner of the ASA. This contract acts as an authority that provides the signature which guarantees that after successful change of an ASA ownership the ALGOs bided from the previous owner will be refunded to him since he does not contain the ASA anymore. Additionally the Algo Delegate Authority receives all of the payments executed by the bidders.
2. **App Services** - this component contains the services that talk with the Algorand Network. The application services are divided into 2 sub-components:
   - *Initialization service* - This service is responsible for proper initialization of all the modules used in the application through various types of transactions executed on the Algorand Network. 
   - *Interaction service* - This service performs the bidding action in the application. The bidding action represents an [Atomic Transfer](https://developer.algorand.org/docs/features/atomic_transfers/) of 4 transactions that will be described in more details later in this tutorial.
3. **App Utilities** - this is the simples component that handles the developer's credentials and the Algorand Network transactions. We won't describe in more details this component because it is common for most projects. This component has 2 sub-components as well:
   - *Credentials* - Handles the developer's credentials and provides us with a client through which we can interact with the network. I followed this [tutorial](https://developer.algorand.org/tutorials/creating-python-transaction-purestake-api/) in order to setup my client using the PureStake API.
   - *Blockchain* - Contains functions that encapsulate and execute basic blockchain transactions on the Algorand Network such as: Payments, AssetTransfer, ApplicationCalls and etc. Those transactions are well described in the [Algorand Developer Documentation](https://developer.algorand.org/docs/).

