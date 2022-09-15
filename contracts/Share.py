import smartpy as sp

"""A data structure for address<->share value string mapping .
"""

    

class Share(sp.Contract):
    """A class Lend contracts for FatCowIO Trading Protocol .
    """
    def __init__(self, administrator,creator, metadata, fa2, fee):
        """Initializes the contracts.
        """
        # Initialize the contracts storage
        self.init(administrator=administrator,
            creator=creator,
            metadata=metadata,
            fa2=fa2,
            fee=fee,
            fee_recipient=administrator,
            proposed_administrator = sp.none,
            checkout_paused=False,
            mapping_items=sp.big_map(
                tkey=sp.TAddress,
                tvalue=sp.TInt,
            ),
        )
        

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contracts
        administrator.
        """
        sp.verify(sp.sender == self.data.administrator, message="MP_NOT_ADMIN")

    def check_no_tez_transfer(self):
        """Checks that no tez were transferred in the operation.
        """
        sp.verify(sp.amount == sp.tez(0), message="MP_TEZ_TRANSFER")



    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contracts administrator to another address.
        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)
        
    @sp.entry_point
    def generate_address_share(self):
        """write the address in to share.
        """
        self.data.mapping_items[sp.sender] = 0
        
    @sp.onchain_view()
    def get_address_share(self):
        """Returns the value from share.
        """
        
        #return the value of add
        sp.result(self.data.mapping_items[sp.sender])
        
    @sp.onchain_view()
    def get_all_share(self):
        """Returns the value from share.
        """
        
        #return the value of add
        sp.result(self.data.mapping_items)
       

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contracts administrator
        responsabilities.
        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(),
                  message="MP_NO_NEW_ADMIN")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(),
                  message="MP_NOT_PROPOSED_ADMIN")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.entry_point
    def set_pause_checkout(self, pause):
        """Pause or not the collects.
        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the collects
        self.data.checkout_paused = pause

    @sp.onchain_view()
    def get_administrator(self):
        """Returns the Event administrator address.
        """
        sp.result(self.data.administrator)



    def fa2_transfer(self, fa2, from_, to_, token_id, token_amount):
        """Transfers a number of editions of a FA2 token between two addresses.
        """
        # Get a handle to the FA2 token transfer entry point
        c = sp.contract(
            t=sp.TList(sp.TRecord(
                from_=sp.TAddress,
                txs=sp.TList(sp.TRecord(
                    to_=sp.TAddress,
                    token_id=sp.TNat,
                    amount=sp.TNat).layout(("to_", ("token_id", "amount")))))),
            address=fa2,
            entry_point="transfer").open_some()

        # Transfer the FA2 token editions to the new address
        sp.transfer(
            arg=sp.list([sp.record(
                from_=from_,
                txs=sp.list([sp.record(
                    to_=to_,
                    token_id=token_id,
                    amount=token_amount)]))]),
            amount=sp.mutez(0),
            destination=c)



sp.add_compilation_target("Share", Share(
    administrator=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    creator=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    fa2=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    fee=sp.nat(25)))