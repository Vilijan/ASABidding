# Algorand Standard Asset bidding application

## Overview

Through this solution I want to explain a system developed on the Algorand blockchain network that does automated transfer of an asset of interest to the person who has paid the most for that particular asset. 

Lets imagine a scenario in the today's world where an entity wants to sell some arbitrary asset for the highest possible price. The process of bidding for the asset and the process of transferring the ownership of the asset involves a lot of 3rd parties which adds a lot of additional costs to the process and adds the need to trust unknown institutions who operate behind the scenes. In this blog post I describe a system that tries to replace the 3rd party institutions with a code which is best described as a Smart Contract. 

We currently relay on a lot of signatures from well established institutions in order verify some processes. What if those signatures can be provided by compiling a deterministic program which is transparent and provides equal opportunity for everyone participating in the process ? 


## Application 

The decentralized application described in this solution has a goal to do automated bidding for a predefined Algorand Standard Asset (ASA). The usage process of the application is the following:

1. Some entity creates an ASA that want to sell on the Algorand blockchain network. This ASA can be mapped to anything in the physical world.
2. Users i.e. bidders who want to buy this ASA will call the application with the specified amount of ALGOs they want to pay.

   - If the current bidder has provided the highest amount of ALGOs the ASA will be automatically transferred to the bidder's wallet. The person who previously held the ASA will get refund for his ALGOs because he is no longer the highest bidder.

   - If the current bidder has provided lower amount of ALGOs than the current highest bidder the App will reject this transaction

The application is developed using PyTeal and 