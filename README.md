# Algorand Standard Asset bidding application

## Overview

Through this solution I want to explain a system developed on the Algorand network that does automated transfer of an asset of interest to the person who has paid the most for that particular asset. 

Lets imagine a scenario in the today's world where an entity wants to sell some arbitrary asset for the highest possible price. The process of bidding for the asset and the process of transferring the ownership of the asset involves a lot of 3rd parties which adds a lot of additional costs to the process and adds the need to trust unknown institutions who operate behind the scenes. In this blog post I describe a system that tries to replace the 3rd party institutions with a code which is best described as a Smart Contract. 

We currently relay on a lot of signatures from well established institutions in order verify some processes. What if those signatures can be provided by compiling a deterministic program which is transparent and provides equal opportunity for everyone participating in the process ? 

## Table of content

[TOC]




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

1. **Application initialization** - from the image above we can see that this code will only run when the application's id is 0 which means that this is the first creation of the application. In this state we want to initialize the global variables of the application to which we know the default values.
```python
def app_initialization_logic():
    return Seq([
        App.globalPut(Bytes(AppVariables.titleOwner), Bytes(DefaultValues.titleOwner)),
        App.globalPut(Bytes(AppVariables.highestBid), Int(DefaultValues.highestBid)),
        Return(Int(1))
    ])
```
2. **Possible application calls** - after we have initialized the application, now we can interact with it only through application calls. In the ASA bidding application we have two possible applications calls:
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
  - Payment to the *algoDelegateAddress* which represents the latest bid for the ASA.
  - Payment from the algoDelegateAddress to the old owner of the ASA which refunds the ALGOs that were paid from the previous bidder
  - Payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one.

3. **Setting up delegates** - In this part of the application we setup the delegate authorities as application variables and also we setup the first owner of the ASA which is the creator of the ASA. With this we are making sure that the transfer of the assets is always happening through the right authorities. The setting up of the delegates can be performed only once.
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

​		Here we are creating optional variables for the *asaDelegateAddress* and the *algoDelegateAddress* values. If those variables  contain some value it means that they are already setup up which should result in a setup failure. If those variables does not contain any value means that we are setting them up for the first time.

4. **Transferring the ASA** - This is the most complex PyTeal code that handles the bidding logic in the application. This code runs when atomic transfer with 4 transaction is executed. The transactions were described previously.
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
- **Second transaction is valid** - the second transaction which is the payment to the *algoDelegateAddress* that represents the latest bid for the ASA is valid when:
  - The transaction type is Payment
  - The first and the second transaction have the same sender, this means that the caller of the application and the bidder are the same
  - If the newly bided amount is bigger than the current highest one
  - If the receiver of the payment i.e bid is the algoDelegateAddress
- **Third transaction is valid** - the third transaction which is payment from the algoDelegateAddress to the old owner of the ASA which refunds the ALGOs that were paid from the previous bidder is valid when:
  - The transaction type is Payment
  - The sender of the transaction is the algoDelegateAddress which is responsible for refunding
  - The receiver of the transaction is the current address that is held in the asaOwnerAddress variable.
  - The payment amount is equal to the current highest bid that is held in the highestBid variable.
- Fourth transaction is valid - the fourth transaction which is payment from the ASADelegateAddress that transfers the ASA from the old owner to the new one is valid when:
  - The transaction type is AssetTransfer
  - The transaction sender is the ASADelegateAddress  which is responsible for transferring the ASA
  - The transaction receiver is the new owner address which is the sender of the first two transactions.

When all of the 4 transactions are valid we update the state of the application and thus the approval program returns that the atomic transfer is valid. If any of those cases fails the approval program will reject the atomic transfer transaction.

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

