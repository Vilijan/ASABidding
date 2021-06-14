from pyteal import *


def application_start(algorealm_creation_code,
                      algorealm_actions_code):
    """
    The app has two main flows. The first one which is the algorealm_creation_code is the code that is run on the first
    initialization of the application. The second branching is the alrealm_actions_code which performs the available
    actions in the game
    :param algorealm_creation_code: PyTeal code for the algorealm_creation_code logic.
    :param algorealm_actions_code: PyTeal code for the algorand_realm_actions_code logic.
    :return:
    """
    is_algorealm_creation = Txn.application_id() == Int(0)
    are_algorealm_actions_used = Txn.on_completion() == OnComplete.NoOp

    return If(is_algorealm_creation, algorealm_creation_code,
              If(are_algorealm_actions_used, algorealm_actions_code, Return(Int(0))))


def algorealm_creation_logic():
    """
    Initializes the global variables of the application.
    :return:
    """
    return Seq([
        App.globalPut(Bytes("RandomicMajestyOfAlgorand"), Bytes("Silvio")),
        App.globalPut(Bytes("VerifiableMajestyOfAlgorand"), Bytes("Silvio")),
        App.globalPut(Bytes("CrownOfEntropyDonation"), Int(0)),
        App.globalPut(Bytes("SceptreOfProofDonation"), Int(0)),
        Return(Int(1))
    ])


def algorealm_application_calls(algorealm_law_promulgation_code,
                                claim_titles_code):
    """
    There are two types of application calls:
    - law promulgation: which is initializes the stateless smart contract address
    into the global variables. This code needs to make sure that the app can execute this logic only once.
    - claiming of the titles: this logic is executed in every other application call after the promulgation of the law.
    It makes sure that the appropriate owner claims the title.
    :param algorealm_law_promulgation_code:
    :param claim_titles_code:
    :return:
    """
    is_law_promulgation = Global.group_size() == Int(1)
    is_claiming_titles = Global.group_size() == Int(3)

    return If(is_law_promulgation, algorealm_law_promulgation_code,
              If(is_claiming_titles, claim_titles_code, Return(Int(0))))


def algorealm_law_promulgation_logic():
    """
    Stores the stateless smart contract address into the AlgoRealmLaw global variable. This code makes sure that the
    AlgoRealmLaw variable is initialized only once and can not be changed.
    :return:
    """
    algo_realm_law_var = App.globalGetEx(Int(0), Bytes("AlgoRealmLaw"))
    law_failure = Seq([
        Return(Int(0))
    ])
    promulgate_law = Seq([
        App.globalPut(Bytes("AlgoRealmLaw"), Txn.application_args[0]),
        Return(Int(1))
    ])

    program = Seq([
        algo_realm_law_var,
        If(algo_realm_law_var.hasValue(), law_failure, promulgate_law)
    ])
    return program


def algrealm_claim_title_atomic_transfer_logic(claim_title_code):
    """
    The application is called in a atomic transfer transaction. The first transaction is the application call which
    takes two arguments ( the name of the title that want to be claimed Crown or Scepter and as the second argument the
    name of the future owner after successful transfer of titles). The second transaction is a payment from the sender
    to the rewards pool. The third transaction is asset transfer from the stateless contract to the future owner.
    :param claim_title_code: PyTeal code for claiming the titles.
    :return:
    """
    first_transaction_is_application_call = Gtxn[0].type_enum() == TxnType.ApplicationCall
    first_transaction_has_two_arguments = Gtxn[0].application_args.length() == Int(2)
    third_transaction_is_asset_transfer = Gtxn[2].type_enum() == TxnType.AssetTransfer

    sender = Gtxn[2].sender()
    true_sender = App.globalGet(Bytes("AlgoRealmLaw"))
    is_the_third_transaction_sent_by_the_smart_contract = sender == true_sender

    atomic_transfer_conditions_satisfied = And(first_transaction_is_application_call,
                                               first_transaction_has_two_arguments,
                                               third_transaction_is_asset_transfer,
                                               is_the_third_transaction_sent_by_the_smart_contract)

    return If(atomic_transfer_conditions_satisfied, claim_title_code, Seq([Return(Int(0))]))


def algorealm_claim_title_logic(claim_crown_code, claim_scepter_code):
    """
    Code that navigates which title should be claimed.
    :param claim_crown_code: PyTeal code logic for claiming the crown.
    :param claim_scepter_code: PyTeal code logic for claiming the scepter.
    :return:
    """
    claiming_title = Gtxn[0].application_args[0]
    is_claiming_crown = claiming_title == Bytes("Crown")
    is_claiming_scepter = claiming_title == Bytes("Sceptre")

    return If(is_claiming_crown, claim_crown_code,
              If(is_claiming_scepter, claim_scepter_code, Return(Int(0))))


def algorealm_claim_single_title_logic(title_name, title_amount_key):
    """
    This code creates the logic for claiming the Crown or Sceptre titles.
    :param title_name: Name of the title either Crown or Sceptre
    :param title_amount_key: Name of the variable that holds the current highest donation CrownOfEntropyDonation or
    SceptreOfProofDonation
    :return:
    """
    paid_amount = Gtxn[1].amount()
    current_max_amount = App.globalGet(Bytes(title_amount_key))
    should_update_title = paid_amount > current_max_amount

    update_title_ownwer = App.globalPut(Bytes(title_name), Gtxn[0].application_args[1])
    update_title_value = App.globalPut(Bytes(title_amount_key), Gtxn[1].amount())

    update_title_logic = Seq([
        update_title_ownwer,
        update_title_value,
        Return(Int(1))
    ])

    return If(should_update_title, update_title_logic, Return(Int(0)))


def clear_program():
    return Return(Int(1))


def algorealm_app():
    claim_crown_of_entropy = algorealm_claim_single_title_logic(title_name="RandomicMajestyOfAlgorand",
                                                                title_amount_key="CrownOfEntropyDonation")

    claim_verifiable_majesty = algorealm_claim_single_title_logic(title_name="VerifiableMajestyOfAlgorand",
                                                                  title_amount_key="SceptreOfProofDonation")

    titles_claim_logic = algorealm_claim_title_logic(claim_crown_code=claim_crown_of_entropy,
                                                     claim_scepter_code=claim_verifiable_majesty)

    algorealm_actions_logic = algrealm_claim_title_atomic_transfer_logic(claim_title_code=titles_claim_logic)

    application_calls_code = algorealm_application_calls(
        algorealm_law_promulgation_code=algorealm_law_promulgation_logic(),
        claim_titles_code=algorealm_actions_logic)

    approval_program = application_start(algorealm_creation_code=algorealm_creation_logic(),
                                         algorealm_actions_code=application_calls_code)

    return approval_program, clear_program()
