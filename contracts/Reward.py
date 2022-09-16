import smartpy as sp

# FA2 standard: https://gitlab.com/tezos/tzip/-/blob/master/proposals/tzip-12/tzip-12.md
# Documentation: https://smartpy.io/docs/guides/FA/FA2

t_balance_of_args = sp.TRecord(
    requests=sp.TList(sp.TRecord(owner=sp.TAddress, token_id=sp.TNat)),
    callback=sp.TContract(
        sp.TList(
            sp.TRecord(
                request=sp.TRecord(owner=sp.TAddress, token_id=sp.TNat), balance=sp.TNat
            ).layout(("request", "balance"))
        )
    ),
).layout(("requests", "callback"))


class Reward(sp.Contract):
    """A class Reward contracts for FatCowIO Trading Protocol "
    """

    def __init__(self, administrator, creator, metadata_base, metadata_url, fa2):
        self.init(
            administrator=administrator,
            creator=creator,
            ledger=sp.big_map(tkey=sp.TNat, tvalue=sp.TAddress),
            metadata=sp.utils.metadata_of_url(metadata_url),
            next_token_id=sp.nat(0),
            operators=sp.big_map(
                tkey=sp.TRecord(
                    owner=sp.TAddress,
                    operator=sp.TAddress,
                    token_id=sp.TNat,
                ).layout(("owner", ("operator", "token_id"))),
                tvalue=sp.TUnit,
            ),
            token_metadata=sp.big_map(
                tkey=sp.TNat,
                tvalue=sp.TRecord(
                    token_id=sp.TNat,
                    token_info=sp.TMap(sp.TString, sp.TBytes),
                ),
            ),
            paused=False,
            proposed_administrator=sp.none,
            fa2=fa2,
        )
        metadata_base["views"] = [
            self.all_tokens,
            self.get_balance,
            self.is_operator,
            self.total_supply,
        ]
        self.init_metadata("metadata_base", metadata_base)

    @sp.entry_point
    def transfer(self, batch):
        """Accept a list of transfer operations.

        Each transfer operation specifies a source: `from_` and a list
        of transactions. Each transaction specifies the destination: `to_`,
        the `token_id` and the `amount` to be transferred.

        Args:
            batch: List of transfer operations.
        Raises:
            `FA2_TOKEN_UNDEFINED`, `FA2_NOT_OPERATOR`, `FA2_INSUFFICIENT_BALANCE`
        """
        with sp.for_("transfer", batch) as transfer:
            with sp.for_("tx", transfer.txs) as tx:
                sp.set_type(
                    tx,
                    sp.TRecord(
                        to_=sp.TAddress, token_id=sp.TNat, amount=sp.TNat
                    ).layout(("to_", ("token_id", "amount"))),
                )
                sp.verify(tx.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
                sp.verify(
                    (transfer.from_ == sp.sender)
                    | self.data.operators.contains(
                        sp.record(
                            owner=transfer.from_,
                            operator=sp.sender,
                            token_id=tx.token_id,
                        )
                    ),
                    "FA2_NOT_OPERATOR",
                )
                with sp.if_(tx.amount > 0):
                    sp.verify(
                        (tx.amount == 1)
                        & (self.data.ledger[tx.token_id] == transfer.from_),
                        "FA2_INSUFFICIENT_BALANCE",
                    )
                    self.data.ledger[tx.token_id] = tx.to_

    @sp.entry_point
    def update_operators(self, actions):
        """Accept a list of variants to add or remove operators.

        Operators can perform transfer on behalf of the owner.
        Owner is a Tezos address which can hold tokens.

        Only the owner can change its operators.

        Args:
            actions: List of operator update actions.
        Raises:
            `FA2_NOT_OWNER`
        """
        with sp.for_("update", actions) as action:
            with action.match_cases() as arg:
                with arg.match("add_operator") as operator:
                    sp.verify(operator.owner == sp.sender, "FA2_NOT_OWNER")
                    self.data.operators[operator] = sp.unit
                with arg.match("remove_operator") as operator:
                    sp.verify(operator.owner == sp.sender, "FA2_NOT_OWNER")
                    del self.data.operators[operator]

    @sp.entry_point
    def balance_of(self, args):
        """Send the balance of multiple account / token pairs to a callback
        address.

        transfer 0 mutez to `callback` with corresponding response.

        Args:
            callback (contracts): Where to callback the answer.
            requests: List of requested balances.
        Raises:
            `FA2_TOKEN_UNDEFINED`, `FA2_CALLBACK_NOT_FOUND`
        """

        def f_process_request(req):
            sp.verify(req.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
            sp.result(
                sp.record(
                    request=sp.record(owner=req.owner, token_id=req.token_id),
                    balance=sp.eif(
                        self.data.ledger[req.token_id] == req.owner, sp.nat(1), 0
                    ),
                )
            )

        sp.set_type(args, t_balance_of_args)
        sp.transfer(args.requests.map(f_process_request), sp.mutez(0), args.callback)

    def check_is_administrator(self):
        """Checks that the address that called the entry point is the contracts
        administrator.
        """
        sp.verify(sp.sender == self.data.administrator,
                  message="MINTER_NOT_ADMIN")

    @sp.entry_point
    def mint(self, to_, metadata):
        """(Admin only) Create a new token with an incremented id and assign
        it. to `to_`.

        Args:
            to_ (address): Receiver of the tokens.
            metadata (map of string bytes): Metadata of the token.
        Raises:
            `FA2_NOT_ADMIN`
        """

        # Check that the contracts is not paused
        sp.verify(~self.data.paused, message="MINT_PAUSED")

        sp.verify(sp.sender == self.data.administrator, "FA2_NOT_ADMIN")
        token_id = sp.compute(self.data.next_token_id)
        self.data.token_metadata[token_id] = sp.record(
            token_id=token_id, token_info=metadata
        )
        self.data.ledger[token_id] = to_
        self.data.next_token_id += 1

    @sp.offchain_view(pure=True)
    def all_tokens(self):
        """Return the list of all the `token_id` known to the contracts."""
        sp.result(sp.range(0, self.data.next_token_id))

    @sp.offchain_view(pure=True)
    def get_balance(self, params):
        """Return the balance of an address for the specified `token_id`."""
        sp.set_type(
            params,
            sp.TRecord(owner=sp.TAddress, token_id=sp.TNat).layout(
                ("owner", "token_id")
            ),
        )
        sp.verify(params.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
        sp.result(sp.eif(self.data.ledger[params.token_id] == params.owner, 1, 0))

    @sp.offchain_view(pure=True)
    def total_supply(self, params):
        """Return the total number of tokens for the given `token_id` if known
        or fail if not."""
        sp.verify(params.token_id < self.data.next_token_id, "FA2_TOKEN_UNDEFINED")
        sp.result(1)

    @sp.offchain_view(pure=True)
    def is_operator(self, params):
        """Return whether `operator` is allowed to transfer `token_id` tokens
        owned by `owner`."""
        sp.result(self.data.operators.contains(params))

    @sp.entry_point
    def transfer_administrator(self, proposed_administrator):
        """Proposes to transfer the contracts administrator to another address.
        """
        # Define the input parameter data type
        sp.set_type(proposed_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Set the new proposed administrator address
        self.data.proposed_administrator = sp.some(proposed_administrator)

    @sp.entry_point
    def accept_administrator(self):
        """The proposed administrator accepts the contracts administrator
        responsabilities.
        """
        # Check that there is a proposed administrator
        sp.verify(self.data.proposed_administrator.is_some(),
                  message="MINTER_NO_NEW_ADMIN")

        # Check that the proposed administrator executed the entry point
        sp.verify(sp.sender == self.data.proposed_administrator.open_some(),
                  message="MINTER_NOT_PROPOSED_ADMIN")

        # Set the new administrator address
        self.data.administrator = sp.sender

        # Reset the proposed administrator value
        self.data.proposed_administrator = sp.none

    @sp.entry_point
    def transfer_fa2_administrator(self, proposed_fa2_administrator):
        """Proposes to transfer the FA2 token contracts administator to another
        minter contracts.
        """
        # Define the input parameter data type
        sp.set_type(proposed_fa2_administrator, sp.TAddress)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Get a handle on the FA2 contracts transfer_administator entry point
        fa2_transfer_administrator_handle = sp.contract(
            t=sp.TAddress,
            address=self.data.fa2,
            entry_point="transfer_administrator").open_some()

        # Propose to transfer the FA2 token contracts administrator
        sp.transfer(
            arg=proposed_fa2_administrator,
            amount=sp.mutez(0),
            destination=fa2_transfer_administrator_handle)

    @sp.entry_point
    def accept_fa2_administrator(self):
        """Accepts the FA2 contracts administrator responsabilities.
        """
        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Get a handle on the FA2 contracts accept_administator entry point
        fa2_accept_administrator_handle = sp.contract(
            t=sp.TUnit,
            address=self.data.fa2,
            entry_point="accept_administrator").open_some()

        # Accept the FA2 token contracts administrator responsabilities
        sp.transfer(
            arg=sp.unit,
            amount=sp.mutez(0),
            destination=fa2_accept_administrator_handle)

    @sp.entry_point
    def set_pause(self, pause):
        """Pause or not minting with the contracts.
        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the administrator executed the entry point
        self.check_is_administrator()

        # Pause or unpause the mints
        self.data.paused = pause

    @sp.onchain_view(pure=True)
    def is_paused(self):
        """Checks if the contracts is paused.
        """
        # Return true if the contracts is paused
        sp.result(self.data.paused)


metadata_base = {
    "name": "FatCow IO",
    "version": "0.1.0",
    "description": "This is the FatCow Reward base template for implementing tickets, implemented using the FA2 (TZIP-012) base.",
    "interfaces": ["TZIP-012", "TZIP-016"],
    "authors": ["SmartPy <https://fatcow.io/#contact>"],
    "homepage": "https://fatcow.io",
    "source": {
        "tools": ["SmartPy"],
        "location": "https://gitlab.com/SmartPy/smartpy/-/raw/master/python/templates/fa2_nft_minimal.py",
    },
    "permissions": {
        "operator": "owner-or-operator-transfer",
        "receiver": "owner-no-hook",
        "sender": "owner-no-hook",
    },
}

if "templates" not in __name__:
    def make_metadata(symbol, name, decimals):
        """Helper function to build metadata JSON bytes values."""
        return sp.map(
            l={
                "decimals": sp.utils.bytes_of_string("%d" % decimals),
                "name": sp.utils.bytes_of_string(name),
                "symbol": sp.utils.bytes_of_string(symbol),
            }
        )


    admin = sp.test_account("Administrator")
    alice = sp.test_account("Alice")
    bob = sp.test_account("Bob")
    tok0_md = make_metadata(name="Token Zero", decimals=1, symbol="FatCowTok0")
    tok1_md = make_metadata(name="Token One", decimals=1, symbol="Tok1")
    tok2_md = make_metadata(name="Token Two", decimals=1, symbol="Tok2")


    @sp.add_test(name="Test")
    def test():
        scenario = sp.test_scenario()
        c1 = Reward(admin.address,
                 admin.address,
                 metadata_base,
                 "https://example.com",
                 fa2=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
                 )
        scenario += c1


    sp.add_compilation_target(
        "FatCowIOReward",
        Reward(admin.address,
            admin.address,
            metadata_base,
            "https://example.com",
            fa2=sp.address("tz1KozzwY6LrGDsZkTPLGwbh13HNezL21JMV"),
            ),
    )
