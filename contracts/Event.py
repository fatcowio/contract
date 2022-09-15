import smartpy as sp

t_ticket_item_state = sp.TVariant(
    created = sp.TAddress,
    sold = sp.TAddress,
    inactive = sp.TAddress,
)

t_ticket_item = sp.TRecord(
    id = sp.TNat,
    address = sp.TAddress,
    token_id = sp.TNat,
    seller = sp.TAddress,
    buyer = sp.TAddress,
    price = sp.TMutez,
    state = t_ticket_item_state
)

t_transfer_batch = sp.TRecord(
    from_=sp.TAddress,
    txs=sp.TList(
        sp.TRecord(
            to_=sp.TAddress,
            token_id=sp.TNat,
            amount=sp.TNat,
        ).layout(("to_", ("token_id", "amount")))
    ),
).layout(("from_", "txs"))

t_transfer_params = sp.TList(t_transfer_batch)

class Event(sp.Contract):
    """A class Event contracts for FatCowIO Trading Protocol .
    """
    def __init__(self, administrator,creator, metadata, fa2, fee, threshold, royalty, revenue, timeend, groupaddress,shareaddress):
        """Initializes the contracts.
        """
        # Initialize the contracts storage
        self.init(
            administrator=administrator,
            creator=creator,
            metadata=metadata,
            fa2=fa2,
            fee=fee,
            fee_recipient=administrator,
            threshold=threshold,
            royalty=royalty,
            revenue=revenue,
            timeend=timeend,
            proposed_administrator=sp.none,
            ticket_paused=False,
            item_id = sp.nat(1),
            ticket_items=sp.big_map(
                tkey=sp.TNat,
                tvalue=t_ticket_item,
            ),
            user_items=sp.big_map(
                tkey=sp.TAddress,
                tvalue=sp.TSet(sp.TNat)
            ),
            groupaddress=groupaddress,
            shareaddress=shareaddress)

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
    def create_ticket_item(self, params):
        """
        list an NFT on Event the parameter is
        sp.TRecord(
            contract_address = sp.TAddress,
            token_id = sp.TNat,
            price = sp.TMutez
        ).layout("contract_address", ("token_id", "price"))
        """
        sp.set_type(
            params,
            sp.TRecord(
                contract_address=sp.TAddress,
                token_id=sp.TNat,
                price=sp.TMutez
            ).layout(("contract_address", ("token_id", "price")))
        )
        sp.verify(params.price > sp.mutez(0), "price must be at least 1 mutez")
        sp.verify(sp.amount == self.data.fee, "fee must be equal to listing fee")

        # current FA2 contracts has no on-chain view
        item_id = self.data.item_id
        item = sp.record(
            id=item_id,
            address=params.contract_address,
            token_id=params.token_id,
            seller=sp.sender,
            buyer=sp.sender,
            price=params.price,
            state=sp.variant("created", sp.sender)
        )
        self.data.ticket_items[item_id] = item
        self.data.item_id += sp.nat(1)


    @sp.entry_point
    def buy_ticket(self, params):
        sp.set_type(
            params,
            sp.TRecord(
                item_id=sp.TNat,
            )
        )

        sp.verify(self.data.ticket_items.contains(params.item_id), "ticket item")
        item = self.data.ticket_items[params.item_id]
        sp.verify(item.price == sp.amount, "transaction token is not enough")
        
        transfer = sp.contract(t_transfer_params, item.address, "transfer").open_some("address is not a FA2 contracts")

        # transfer amount
        sp.transfer(sp.list([
            sp.record(
                from_=item.seller,
                txs=sp.list([
                    sp.record(
                        to_=sp.sender,
                        token_id=item.token_id,
                        amount=sp.nat(1)
                    )
                ])
            )
        ], t=t_transfer_batch), sp.tez(0), transfer)
        
        
        # calculate the profit
        #sp.send(item.seller, sp.amount)
        
        #to-do fee, threshold, royalty, revenue
        #fee
        #threshold
        #royalty
        #revenue
        
        # add the item to user purchase list
        self.data.user_items[sp.sender].add(item.id)
        # update ticket buyer  
        item.buyer = sp.sender
        # update the item state
        # change status sold in ticket_items list  
        item.state = sp.variant("sold", sp.source)
        

    @sp.entry_point
    def checkout_event(self, params):
        
        sp.set_type(
            params,
            sp.TRecord(
                share_address=sp.TAddress,
            )
        )
     
        #check admin role
        self.check_is_administrator()
        #to-do fee, threshold, royalty, revenue
        #fee
        #threshold
        #royalty
        #call share contract get all address value
        c_share = sp.contract(sp.TInt, self.data.shareaddress, entry_point = "get_all_share").open_some()
        sp.transfer(-42, sp.mutez(0), c_share)
        #checkoput all revenue
        #c_share_pause = sp.contract(sp.TInt, self.data.shareaddress, entry_point = "set_pause_checkout").open_some()
        
        #finish pause event and share 
        #contract = sp.self_entry_point(entry_point = 'set_pause_buy')
        #self.set_pause_buy(True)
        
     

    @sp.entry_point
    def delete_ticket_item(self, params):
        """
        make the item inactive
        """
        sp.set_type(params, sp.TNat)
        sp.verify(params < self.data.item_id, "id must < current id")
        sp.verify(self.data.ticket_items.contains(params), "item is not exists")
        item = self.data.ticket_items[params]
        with sp.if_(item.state.is_variant("created")):
            item.state = sp.variant("inactive", sp.sender)

    @sp.entry_point
    def update_fee(self, new_fee):
        """Updates the Event management fees.
        """
        # Define the input parameter data type
        sp.set_type(new_fee, sp.TMutez)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the new fee is not larger than 25%
        sp.verify(new_fee <= sp.mutez(0), message="MP_WRONG_FEES")

        # Set the new management fee
        self.data.fee = new_fee

    @sp.entry_point
    def update_fee_recipient(self, new_fee_recipient):
        """Updates the Event management fee recipient address.
        """
        # Define the input parameter data type
        sp.set_type(new_fee_recipient, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new management fee recipient address
        self.data.fee_recipient = new_fee_recipient

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
    def set_pause_buy(self, pause):
        """Pause or not the collects.
        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the collects
        self.data.ticket_paused = pause

    @sp.onchain_view()
    def get_administrator(self):
        """Returns the Event administrator address.
        """
        sp.result(self.data.administrator)

    @sp.onchain_view()
    def get_fee(self):
        """Returns the Event fee.
        """
        sp.result(self.data.fee)

    @sp.onchain_view()
    def get_fee_recipient(self):
        """Returns the Event fee recipient address.
        """
        sp.result(self.data.fee_recipient)

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


sp.add_compilation_target("Event", Event(
    administrator=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    creator=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    fa2=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    fee=sp.mutez(1),
    threshold=sp.utils.metadata_of_url("ipfs://thold"),
    royalty=sp.nat(100),
    revenue=sp.nat(100),
    timeend=sp.nat(10000),
    groupaddress=sp.address("tz1KozzwY6L21JMV"),
    shareaddress=sp.address("tz1KozzwY6LrGDMV"),
    ))