import smartpy as sp

t_ticket_item_state = sp.TVariant(
    created = sp.TAddress,
    release = sp.TAddress,
    inactive = sp.TAddress,
)

t_ticket_item = sp.TRecord(
    id = sp.TNat,
    address = sp.TAddress,
    token_id = sp.TNat,
    seller = sp.TAddress,
    buyer = sp.TOption(sp.TAddress),
    price = sp.TMutez,
    state = t_ticket_item_state
)

t_operator_permission = sp.TRecord(
    owner=sp.TAddress, operator=sp.TAddress, token_id=sp.TNat
).layout(("owner", ("operator", "token_id")))

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

class Group(sp.Contract):
    """A class Event contracts for FatCowIO Trading Protocol .
    """
    def __init__(self, administrator,creator, metadata, fa2, fee, threshold, royalty, revenue, timeend, groupaddress):
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
            collects_paused=False,
            ticket_items=sp.big_map(
                tkey=sp.TNat,
                tvalue=t_ticket_item,
            ),
            user_items=sp.big_map(
                tkey=sp.TAddress,
                tvalue=sp.TList(sp.TNat)
            ),
            groupaddress=groupaddress)

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
    def crerate_ticket_item(self, params):
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
        sp.verify(sp.amount == self.data.list_fee, "fee must be equal to listing fee")

        # current FA2 contracts has no on-chain view
        is_operator = sp.contract(
            t_operator_permission,
            params.contract_address,
            "is_operator"
        ).open_some("is_operator must be defined")

        item_id = self.data.item_id
        item = sp.record(
            id=item_id,
            address=params.contract_address,
            token_id=params.token_id,
            seller=sp.sender,
            buyer=sp.none,
            price=params.price,
            state=sp.variant("created", sp.sender)
        )
        self.data.ticket_items[item_id] = item
        with sp.if_(self.data.user_items.contains(sp.sender)):
            self.data.user_items[sp.sender].push(item_id)
        with sp.else_():
            self.data.user_items[sp.sender] = sp.list([item_id], t=sp.TNat)

        self.data.item_id += sp.nat(1)

    @sp.entry_point
    def create_ticket_sale(self, params):
        sp.set_type(
            params,
            sp.TRecord(
                address=sp.TAddress,
                item_id=sp.TNat
            ).layout(("address", "item_id"))
        )
        sp.verify(self.data.ticket_items.contains(params.item_id), "item is not exists")
        item = self.data.ticket_items[params.item_id]
        sp.verify(item.price == sp.amount, "please the asking price")
        transfer = sp.contract(t_transfer_params, params.address, "transfer").open_some("address is not a FA2 contracts")

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

        profit = sp.amount - self.data.list_fee
        sp.send(self.data.owner_address, self.data.list_fee)
        sp.send(item.seller, profit)

        item_id = item.id

        with sp.if_(self.data.user_items.contains(sp.sender)):
            self.data.user_items[sp.sender].push(item_id)
        with sp.else_():
            self.data.user_items[sp.sender] = sp.list([item_id], t=sp.TNat)

        item.buyer = sp.some(sp.sender)
        item.state = sp.variant("release", sp.sender)

    @sp.entry_point
    def list_ticket(self, params):
        sp.set_type(
            params,
            sp.TRecord(address = sp.TAddress,
                       token_id = sp.TNat,
                       price = sp.TMutez)
        )
        sp.verify(params.price > sp.mutez(0), "price must be at lease 1 mutez")
        sp.verify(sp.amount == self.data.fee, "fee must be equal to the listing ")
        item_id = self.data.next_item_id
        item = sp.record(
            id=item_id,
            address=params.address,
            token_id=params.token_id,
            seller=sp.source,
            buyer=sp.none,
            state=sp.varint("created", sp.source)
        )
        # store in to the market database
        self.data.ticket_items[item_id] = item
        # update the user record
        self.data.my_listed_items[sp.source][item_id] = sp.unit
        # charge the list fee
        sp.send(self.owner, self.data.fee)
        # increase the item id
        self.data.next_item_id += 1

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
        transfer_call = sp.contract(t_transfer_params, item.address, "transfer")
        # call FA2
        sp.transfer(sp.list([sp.record(
                from_=item.seller,
                txs=sp.list([
                    sp.record(
                        to_=sp.sender,
                        token_id=item.id,
                        amount=sp.nat(1)
                    )
                ])
            )
        ], t=t_transfer_batch), sp.tez(0), transfer_call)
        # calculate the profit
        sp.send(item.seller, sp.amount)
        # update the purchase list
        self.data.my_purchase_items[sp.source][item.id] = sp.unit
        # update the listed list
        del self.data.my_listed_items[item.seller][item.id]
        # update the item state
        item.state = sp.varint("release", sp.source)
        self.ticket_items[item.id] = item

    @sp.entry_point
    def collect(self, swap_id):
        """Collects one edition of a token that has already been swapped.
        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that collects are not paused
        sp.verify(~self.data.collects_paused, message="MP_COLLECTS_PAUSED")

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id), message="MP_WRONG_SWAP_ID")

        # Check that the collector is not the creator of the swap
        swap = sp.local("swap", self.data.swaps[swap_id])
        sp.verify(sp.sender != swap.value.issuer, message="MP_IS_SWAP_ISSUER")

        # Check that there is at least one edition available to collect
        sp.verify(swap.value.editions > 0, message="MP_SWAP_COLLECTED")

        # Check that the provided mutez amount is exactly the edition price
        sp.verify(sp.amount == swap.value.price, message="MP_WRONG_TEZ_AMOUNT")

        # Handle tez tranfers if the edition price is not zero
        with sp.if_(sp.amount != sp.mutez(0)):
            # Get the royalties information from the FA2 token contracts
            royalties = sp.local(
                "royalties", self.get_token_royalties(swap.value.token_id))

            # Send the royalties to the token minter
            minter_royalties_amount = sp.local(
                "minter_royalties_amount", sp.split_tokens(
                    sp.amount, royalties.value.minter.royalties, 1000))

            with sp.if_(minter_royalties_amount.value > sp.mutez(0)):
                sp.send(royalties.value.minter.address,
                        minter_royalties_amount.value)

            # Send the royalties to the token creator
            creator_royalties_amount = sp.local(
                "creator_royalties_amount", sp.split_tokens(
                    sp.amount, royalties.value.creator.royalties, 1000))

            with sp.if_(creator_royalties_amount.value > sp.mutez(0)):
                sp.send(royalties.value.creator.address,
                        creator_royalties_amount.value)

            # Send the management fees
            fee_amount = sp.local(
                "fee_amount", sp.split_tokens(sp.amount, self.data.fee, 1000))

            with sp.if_(fee_amount.value > sp.mutez(0)):
                sp.send(self.data.fee_recipient, fee_amount.value)

            # Send the donations
            donation_amount = sp.local("donation_amount", sp.mutez(0))
            total_donations_amount = sp.local(
                "total_donations_amount", sp.mutez(0))

            with sp.for_("org_donation", swap.value.donations) as org_donation:
                donation_amount.value = sp.split_tokens(
                    sp.amount, org_donation.donation, 1000)

                with sp.if_(donation_amount.value > sp.mutez(0)):
                    sp.send(org_donation.address, donation_amount.value)
                    total_donations_amount.value += donation_amount.value

            # Send what is left to the swap issuer
            sp.send(swap.value.issuer,
                    sp.amount -
                    minter_royalties_amount.value -
                    creator_royalties_amount.value -
                    fee_amount.value -
                    total_donations_amount.value)

        # Transfer the token edition to the collector
        self.fa2_transfer(
            fa2=self.data.fa2,
            from_=sp.self_address,
            to_=sp.sender,
            token_id=swap.value.token_id,
            token_amount=1)

        # Update the number of editions available in the swaps big map
        self.data.swaps[swap_id].editions = sp.as_nat(swap.value.editions - 1)

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
        sp.set_type(new_fee, sp.TNat)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the new fee is not larger than 25%
        sp.verify(new_fee <= 250, message="MP_WRONG_FEES")

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
    def set_pause_collects(self, pause):
        """Pause or not the collects.
        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the collects
        self.data.collects_paused = pause

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

    def get_token_royalties(self, token_id):
        """Gets the token royalties information calling the FA2 contracts
        on-chain view.
        """
        return sp.view(
            name="token_royalties",
            address=self.data.fa2,
            param=token_id,
            t=sp.TRecord(
                minter=Group.USER_ROYALTIES_TYPE,
                creator=Group.USER_ROYALTIES_TYPE).layout(
                        ("minter", "creator"))
            ).open_some()


sp.add_compilation_target("Group", Group(
    administrator=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    creator=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    fa2=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    fee=sp.nat(25),
    threshold=sp.utils.metadata_of_url("ipfs://thold"),
    royalty=sp.nat(25),
    revenue=sp.nat(25),
    timeend=sp.nat(25),
    groupaddress=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
    ))