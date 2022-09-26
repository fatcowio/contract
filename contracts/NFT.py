from enum import Enum

import smartpy as sp

FA2 = sp.io.import_script_from_url("https://smartpy.io/templates/fa2_lib.py")


class NFTStatus(Enum):
    MINTED = 1
    CLAIMED = 2
    VOID = 3


class NFT(
    FA2.Admin,
    FA2.OffchainviewTokenMetadata,
    FA2.MintNft,
    FA2.Fa2Nft,
):
    def __init__(self, administrator, **kwargs):
        FA2.Fa2Nft.__init__(self, **kwargs)
        FA2.Admin.__init__(self, administrator)
        self.update_initial_storage(
            # The big map with the token's status
            token_status=sp.big_map({}, tkey=sp.TNat, tvalue=sp.TNat),
        )

    @sp.entry_point
    def mint(self, batch):
        """Admin can mint new or existing tokens."""
        sp.verify(self.is_administrator(sp.sender), "FA2_NOT_ADMIN")
        with sp.for_("action", batch) as action:
            token_id = sp.compute(self.data.last_token_id)
            metadata = sp.record(token_id=token_id, token_info=action.metadata)
            self.data.token_metadata[token_id] = metadata
            self.data.ledger[token_id] = action.to_
            self.data.token_status[token_id] = NFTStatus.MINTED.value
            self.data.last_token_id += 1

    @sp.onchain_view(pure=True)
    def is_claimed(self, token_id):
        """If the token has been claimed yet"""
        sp.set_type(token_id, sp.TNat)
        self.is_defined(token_id)
        sp.result(self.data.token_status[token_id] == NFTStatus.CLAIMED.value)


sp.add_compilation_target(
    "nft",
    NFT(
        administrator=sp.address("tz1ZMPhZxGEdvi4vumphBsXhDBNRggNX6rXH"),
        metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    ),
)