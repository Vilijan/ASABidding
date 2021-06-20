# Algorand Standard Asset bidding application

## Environment setup

- `pip install requirements.txt`

- Configure a `config.yml` file with the properties shown below:

  ```yaml
  client_credentials:
    token: TOKEN_VALUE
    address: ADDRESS_VALUE
  
  main_developer_credentials:
    private_key: PRIVATE_KEY_VALUE
    public_key: PUBLIC_KEY_VALUE
  
  developer_1_credentials:
    private_key: PRIVATE_KEY_VALUE
    public_key: PUBLIC_KEY_VALUE
  ```

## Overview

Through this solution I want to explain a system developed on the Algorand network that does automated transfer of an asset of interest to the person who has paid the most for that particular asset. 

Lets imagine a scenario in the today's world where an entity wants to sell some arbitrary asset for the highest possible price. The process of bidding for the asset and the process of transferring the ownership of the asset involves a lot of 3rd parties which adds a lot of additional costs to the process and adds the need to trust unknown institutions who mostly operate behind the scenes. In this blog post I describe a system that tries to replace the 3rd party institutions with a code which is best described as a Smart Contract. 

We currently relay on a lot of signatures from well established institutions in order verify some processes. What if those signatures can be provided by compiling a deterministic program which is transparent and provides equal opportunity for everyone participating in the process ? 

## Table of Content

- [Algorand Standard Asset bidding application](#algorand-standard-asset-bidding-application)
  * [Overview](#overview)
  * [Application Usage](#application-usage)
  * [Application architecture](#application-architecture)
  * [PyTeal Components](#pyteal-components)
    + [App Source Code](#app-source-code)
    + [ASA Delegate authority](#asa-delegate-authority)
    + [Algo Delegate Authority](#algo-delegate-authority)
  * [Application Services](#application-services)
    + [Application Initialization Service](#application-initialization-service)
    + [Application interaction service](#application-interaction-service)
  * [Application deployment on Algorand TestNet network](#application-deployment-on-algorand-testnet-network)
    + [Initialization of the application](#initialization-of-the-application)
    + [First bidding for the ASA](#first-bidding-for-the-asa)
    + [Second bidding for the ASA](#second-bidding-for-the-asa)
  * [Final thoughts](#final-thoughts)


## Application Usage

The decentralized application described in this solution has a goal to do automated bidding for a predefined Algorand Standard Asset (ASA). The usage process of the application is the following:

1. Some entity creates an ASA that wants to sell on the Algorand blockchain network. This ASA can be mapped to anything in the physical world. In this step the entity deploys a single instance of the application that handles the bidding for the defined ASA.
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
   - *Blockchain* - Contains functions that encapsulate and execute basic blockchain transactions on the Algorand Network such as: Payments, AssetTransfer, ApplicationCalls, etc. Those transactions are well described in the [Algorand Developer Documentation](https://developer.algorand.org/docs/).

## PyTeal Components

In this section I will describe in more details the logic behind the PyTeal code that is used in this application. 

### App Source Code

The [app source module](https://github.com/Vilijan/ASABidding/blob/main/src/app_pyteal/app_source_code.py) contains all of the logic for the Stateful Smart Contract which represents the ASA bidding application. The application has 5 global variables shown in the code snippet below.
```python
class AppVariables:
    titleOwner = "TitleOwner"
    highestBid = "HighestBid"
    asaOwnerAddress = "OwnerAddress"
    asaDelegateAddress = "ASADelegateAddress"
    algoDelegateAddress = "AlgoDelegateAddress"
```

- **Title Owner** - string variable that defines the name of the current ASA owner. During a bidding application call this name is provided as an argument to the application call by the bidder.
- **Highest bid** - integer variable that represents the current highest bid that the owner of the ASA paid. 
- **ASA Owner Address** - the owner of the address that contain the ASA. After a successful bidding application call this property is set to the sender of the bidder application call.
- **ASA Delegate Address** - the address of the *ASA Delegate Authority* that is responsible for transferring the ASA. This variable can be set only once in the application.
- **ALGO Delegate Address** - the address of the *ALGO Delegate Authority* that is responsible for refunding the ALGOs to the previous ASA owner. This variable can be set only once in the application.

The application can be executed in three different flows, the first one is the application initialization which is executed when the transaction is created. The second and the third flows are actions that can be performed on the application such as: setting up delegate authorities and executing a bidding.

```python
def application_start(initialization_code,
                      application_actions):
    is_app_initialization = Txn.application_id() == Int(0)
    are_actions_used = Txn.on_completion() == OnComplete.NoOp

    return If(is_app_initialization, initialization_code,
              If(are_actions_used, application_actions, Return(Int(0))))
```

#### Application initialization

From the image above we can see that this code will only run when the application's id is 0 which means that this is the first creation of the application. In this state we want to initialize the global variables of the application to which we know the default values.

```python
def app_initialization_logic():
    return Seq([
        App.globalPut(Bytes(AppVariables.titleOwner), Bytes(DefaultValues.titleOwner)),
        App.globalPut(Bytes(AppVariables.highestBid), Int(DefaultValues.highestBid)),
        Return(Int(1))
    ])
```
#### Possible application calls

After we have initialized the application, now we can interact with it only through application calls. In the ASA bidding application we have two possible applications calls:

```python
def setup_possible_app_calls_logic(assets_delegate_code, transfer_asa_logic):
    is_setting_up_delegates = Global.group_size() == Int(1)
    is_transferring_asa = Global.group_size() == Int(4)

    return If(is_setting_up_delegates, assets_delegate_code,
              If(is_transferring_asa, transfer_asa_logic, Return(Int(0))))
```

- **Setting up delegates** - App call with 3 arguments: ASADelegateAddress, AlgoDelegateAddress and asaOwnerAddress. This application call should be allowed to be executed only once. 
- **Transferring the ASA** - Atomic transfer with 4 transactions which represents a single bidding.
  - Application call with arguments *new_owner_name: string*
  - Payment to the *algoDelegateAddress* which represents the bid for the ASA.
  - Payment from the algoDelegateAddress to the old owner of the ASA which refunds the ALGOs that were paid from the previous bidder
  - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.

#### Setting up delegates

In this part of the application we setup the delegate authorities as application variables and also we setup the first owner of the ASA which is the creator of the ASA. With this we are making sure that the transfer of the assets is always happening through the right authorities. The setting up of the delegates can be performed only once.

```python
def setup_asset_delegates_logic():
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
        If(Or(asa_delegate_authority.hasValue(), algo_delegate_authority.hasValue()), 
           setup_failed, setup_delegates)
    ])
```

​		Here we are creating optional variables for the *asaDelegateAddress* and the *algoDelegateAddress* values. If those variables  contain some value it means that they have already been set up which should result in a setup failure. If those variables does not contain any value it means that we are setting them up for the first time.

#### Transferring the ASA

This is the most complex PyTeal code that handles the bidding logic in the application. This code runs when atomic transfer with 4 transaction is executed. The atomic transfer transactions were described previously in the *Possible action calls* section.

```python
def asa_transfer_logic():
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
```

The updating of the ASA ownership can be summarized in the following steps

- **First transaction is valid**  - the first transaction which is the application call is valid when the transaction type is *ApplicationCall* and when we have passed only one argument which is the name of the bidder.
- **Second transaction is valid** - the second transaction which is the payment to the *algoDelegateAddress* that represents the bid for the ASA is valid when:
  - The transaction type is Payment
  - The first and the second transaction have the same sender, this means that the caller of the application and the bidder are the same
  - If the newly bided amount is bigger than the current highest one
  - If the receiver of the payment i.e bid is the algoDelegateAddress
- **Third transaction is valid** - the third transaction which is payment from the algoDelegateAddress to the old owner of the ASA which refunds the ALGOs that were paid from the previous bidder is valid when:
  - The transaction type is Payment
  - The sender of the transaction is the algoDelegateAddress which is responsible for refunding
  - The receiver of the transaction is the current address that is held in the asaOwnerAddress variable.
  - The payment amount is equal to the current highest bid that is held in the highestBid variable.
- **Fourth transaction is valid** - the fourth transaction which is asset transfer from the ASADelegateAddress that transfers the ASA from the old owner to the new one is valid when:
  - The transaction type is AssetTransfer
  - The transaction sender is the ASADelegateAddress  which is responsible for transferring the ASA
  - The transaction receiver is the new owner address which is the sender of the first two transactions.

When all of the 4 transactions are valid we update the state of the application and thus the approval program returns that the atomic transfer is valid. If any of those cases fails the approval program will reject the atomic transfer transaction.

The *ASA Delegate Authority* will make sure that we are transferring the correct ASA.

In the end we combine everything to get the approval and the clear programs.

```python
def approval_program():
    return application_start(initialization_code=app_initialization_logic(),
                             application_actions=
                             setup_possible_app_calls_logic(assets_delegate_code=setup_asset_delegates_logic(),
                                                            transfer_asa_logic=asa_transfer_logic()))


def clear_program():
    return Return(Int(1))
```

### ASA Delegate authority

The *ASA Delegate Authority* is the Stateless Smart Contract that is responsible for transferring the ASA to the rightful owner. This contract logic is executed in the 4th transaction of the Atomic transfer. This authority needs to make sure that the right application is being called and the correct ASA token is being transferred. 

```python
def asa_delegate_authority_logic(app_id: int, asa_id: int):
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
```

After we compile this PyTeal code we will obtain a unique address that will represent the **ASADelegateAddress** in our application for the provided **app_id** and **asa_id**.

### Algo Delegate Authority

The *Algo Delegate Authority* is the Stateless Smart Contract that is responsible for refunding ALGOs to the previous owner after change of ownership. This contract logic is executed in the 3rd transaction of the Atomic transfer. This authority needs to make sure that the right application is being called.

```python
def algo_delegate_authority_logic(app_id: int):
    is_calling_right_app = Gtxn[0].application_id() == Int(app_id)
    is_acceptable_fee = Gtxn[2].fee() <= Int(1000)
    is_valid_close_to_address = Gtxn[2].asset_close_to() == Global.zero_address()
    is_valid_rekey_to_address = Gtxn[2].rekey_to() == Global.zero_address()

    return And(is_calling_right_app,
               is_acceptable_fee,
               is_valid_close_to_address,
               is_valid_rekey_to_address)
```

After we compile this PyTeal code we will obtain a unique address that will represent the **AlgoDelegateAddress** in our application for the provided **app_id**.

## Application Services

The purpose of Application Services is to decouple the code of the application that interacts with the Algorand network. This way of decoupling the code enables us to build different UIs for the application without ever touching the core part of the code. In principle we should be able to build mobile application, CLI application or web application while the Application Services remain unchanged. On top of that this makes the application more readable and easier to maintain.

### Application Initialization Service

This service is responsible for initialization of the application. After executing all of the required methods in this service we will end up with an application deployed on the TestNet that is ready to accept biddings for the ASA of interest.

#### Initialization of the service

```python
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
```
In order to start the initialization of the service we must provide the app's creator private key and it's public address. Additionally we must provide the unit name and the asset name in order to create the Algorand Standard Asset that will be interacted through this application. In the initialization of this service we retrieve the *Approval Program* and the *Clear Program* that were defined in the App Source Code section. We as well will initialize a client property which is an algod.AlgodClient object that enables us the interaction with the Algorand network.

At the end we will have the correct values for the following properties: *app_id*, *asa_id*, *asa_delegate_authority_address* and *algo_delegate_authority_address*.

#### Creating the application

```python
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
```

In this method call we compile the teal code created using the PyTeal sdk and submit an application transaction with the appropriate parameters. If this transaction succeed we have deployed our bidding application on the Algorand TestNet network.

#### ASA Creation

In this method we create the Algorand Standard Asset for which the users will bid through the application. We should note here that the we set the ASA to be frozen because we want the transferring of the ASA to be only through the *ASA Delegate Authority* address

```python
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

```

#### Setting up ASA Delegate Authority

In this method we compile the PyTeal code used for the ASA Delegate Authority for the previously created **app_id** and **asa_id**. At the end we receive an asa_delegate_authority_address which represents a unique address that can act as any other address on the network. Note that if we compile the asa_delegate_authority_logic with different app_id or asa_id we will end up with different address.

```python
    def setup_asa_delegate_smart_contract(self):
        
        asa_delegate_authority_compiled = compileTeal(asa_delegate_authority_logic(app_id=self.app_id,
                                                                                   asa_id=self.asa_id),
                                                      mode=Mode.Signature,
                                                      version=self.teal_version)

        asa_delegate_authority_bytes = blockchain_utils.compile_program(client=self.client,
                                                                       source_code=asa_delegate_authority_compiled)

        self.asa_delegate_authority_address = algo_logic.address(asa_delegate_authority_bytes)
```
#### Depositing fee funds to the ASA Delegate Authority

Here we just deposit some ALGOs to the ASA Delegate Authority for transaction fees. Note that if the authority addresses run out of ALGO the application won't work because they would not be able to pay the fees to the Algorand Network.

```python
    def deposit_fee_funds_to_asa_delegate_authority(self):
        
        blockchain_utils.execute_payment(client=self.client,
                                         sender_private_key=self.app_creator_pk,
                                         reciever_address=self.asa_delegate_authority_address,
                                         amount=1000000)
```
#### Changing the management of the ASA

After the first creation of the ASA we have set up the management credentials to the creator of the application. We want to remove all the management properties of the ASA so they could not be modified in the future. The only thing that we want to set up is the *clawback_address* property to be the address of the ASA Delegate Authority. In this way only that address can act as an clawback for the ASA.

```python
    def change_asa_credentials(self):
        blockchain_utils.change_asa_management(client=self.client,
                                               current_manager_pk=self.app_creator_pk,
                                               asa_id=self.asa_id,
                                               manager_address="",
                                               reserve_address=None,
                                               freeze_address="",
                                               clawback_address=self.asa_delegate_authority_address)
```

#### Setting up Algo Delegate Authority

In this method we compile the PyTeal code used for the Algo Delegate Authority for the previously created **app_id**. At the end we receive an algo_delegate_authority_address which represents a unique address that can act as any other address on the network. Note that if we compile the algo_delegate_authority_logic with different app_id we will end up with different address.

```python
    def setup_algo_delegate_smart_contract(self):
        algo_delegate_authority_compiled = compileTeal(algo_delegate_authority_logic(app_id=self.app_id),
                                                       mode=Mode.Signature,
                                                       version=self.teal_version)

        algo_delegate_authority_bytes = blockchain_utils.compile_program(client=self.client,
                                                                      source_code=algo_delegate_authority_compiled)

        self.algo_delegate_authority_address = algo_logic.address(algo_delegate_authority_bytes)
```
At the end we also deposit some ALGO funds to the *algo_delegate_authority_address* for transaction fees.

#### Setting up the delegate authorities in the application variables

As we have described previously we need to call the application only once in order to set up the asaDelegateAddress, algoDelegateAddress and asaOwnerAddress global properties of the application. We pass those values as parameters to the application. When we pass the addresses as arguments we need to decode the 32 bytes string address into its address bytes and checksum.

```python
    def setup_app_delegates_authorities(self):
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
```

### Application interaction service

The application interaction service is responsible for executing bidding calls for the specified asa_id to the application with a specified app_id. 

#### Initialization of the interaction service

In order to initialize the interaction service we need to provide the *app_id* and the *asa_id* with which this service will interact. Since the interaction with the application also depends on the state of the application we need to provide the address of the current owner of the ASA and what is the current highest bided amount.

```python
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
```

#### Executing bidding call

The bidding call consists of atomic transfer of 4 transactions that were described in more details in the previous sections. In order to execute a bidding we need to provide the bidder name which is sent as an argument in the first transaction, the bidder's private key and address and the bided amount for the asset. If the transactions are approved by the Stateful and the Stateless Smart Contracts a change of ownership of the ASA will happen.

```python
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
```

## Application deployment on Algorand TestNet network

The final thing that is left for us is to deploy and test the application on the network. 

### Initialization of the application

As the described earlier we can initialize the application with the *AppInitializationService* using the following steps:

```python
app_initialization_service = AppInitializationService(app_creator_pk=main_dev_pk,
                                                      app_creator_address=main_dev_address,
                                                      asa_unit_name="wawa",
                                                      asa_asset_name="wawa",
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
After executing this code we deploy and initialize the application on the TestNet. We can print the properties of the deployed app an inspect them on the [AlgoExplorer](https://testnet.algoexplorer.io/)
```python
app_id: 17026927 
asa_id: 17026938 
asa_delegate_authority_address: U4R3SREIQFAVNCOMQITD4RWNH5LHCSO4BVAIWEJGNVVMLIYTHWXXPZ3Z5I 
algo_delegate_authority_address: L3S72BCRBIY3V42GUNRERKDJ3ENIODBGJFAF53QJILJTBH5NTJQMYOZ6NU
```

If we inspect the global state of the application with id: 17026927 we see the following properties as expected:

![Initialized app global state](https://github.com/Vilijan/ASABidding/blob/main/images/ApplicationGlobalState_AfterInitialization.png?raw=true)

We can also inspect the technical properties of the ASA with id: 17026938

![ASA Technical Properties](https://github.com/Vilijan/ASABidding/blob/main/images/ASA_TechnicalInformation.png?raw=true)

We can see that the *Clawback Account* in the ASA is identical to the *ASA Delegate Address* in our application.

### First bidding for the ASA

After initialization of the application we can use the AppInteractionService to execute bidding transaction calls to the app. Lets execute our first bid with the following code.

```python
app_interaction_service = AppInteractionService(app_id=app_initialization_service.app_id,
                                                asa_id=app_initialization_service.asa_id,
                                                current_owner_address=main_dev_address,
                                                teal_version=3)

app_interaction_service.execute_bidding(bidder_name="Alice",
                                        bidder_private_key=bidder_pk,
                                        bidder_address=bidder_address,
                                        amount=3000000)
```
After the execution we get the following transaction id
```python
Transaction TO55W6TK7IU7YG6FV6XECFFDGZQGKW5EQT5ECYGA4LFJICJMIJIA confirmed in round 14892176.
```
Since this transaction is an atomic transfer it has specific *group_id*. We inspect this *group_id* on the network as well and the application global state to see what has happened.

#### Atomic transfer overview

![First Atomic Transfer Overview](https://github.com/Vilijan/ASABidding/blob/main/images/FirstBidding_GroupID.png?raw=true)

We can see that the ASA has been transferred to the new owner, the old ALGOs were refunded to the old owner of the ASA and the new bid ALGOs has been transferred to the *Algo Delegate Authority address.*

#### Application state overview

![Bid 1 Application State](https://github.com/Vilijan/ASABidding/blob/main/images/FirstBidding_AppGlobalState.png?raw=true)

We can see that the state of the application has been changed as expected. The *HighestBid* has been updated as well with the *TitleOwner* and the *OwnerAddress*.

### Second bidding for the ASA

We can execute second bidding with higher amount to test whether the ownership of the ASA will change.

```python
app_interaction_service.execute_bidding(bidder_name="Bob",
                                        bidder_private_key=main_dev_pk,
                                        bidder_address=main_dev_address,
                                        amount=5000000)
```

We get the following transaction id

```python
Transaction IKI47OJU7XDZI6ATJJ75O44SM4DGWYWR6UDQQFAMM3JBIHBMVAAA confirmed in round 14892335.
```

#### Atomic transfer overview

![Second Bid Atomic Transfer](https://github.com/Vilijan/ASABidding/blob/main/images/SecondBid_GroupTransaction.png?raw=true)

We can see that the ASA has been transferred to the new owner, the old ALGOs were refunded to the old owner of the ASA and the new bid ALGOs has been transferred to the *Algo Delegate Authority address.*

#### Application state overview

![Bid 2 App State](https://github.com/Vilijan/ASABidding/blob/main/images/SecondBid_AppState.png?raw=true)

We can see that the application state has been updated accordingly to match the newest highest bid.

## Final thoughts

If you have made it this far I want to sincerely thank you for reading this solution. I hope that you learned something new and interesting as it was the case for me. 

I strongly believe that we are just starting to scratch the surface of the usage of smart contracts through creating different Decentralized Applications. I think that a lot of systems in the future will depend on signatures from smart contracts instead of some legal authorities. There is a really exciting future ahead of us :)

***This solution is intended for learning purposes only. It does not cover error checking and other edge cases therefore, should not be used as a production application.***

I want to thanks [Cossimo Bassi](https://developer.algorand.org/u/cusma/) for making a tutorial on using smart contracts in the [Algo Realm Game](https://developer.algorand.org/solutions/algorealm-nft-royalty-game/) which inspired me to make this application.
