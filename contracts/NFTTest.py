import smartpy as sp

nft_module = sp.io.import_script_from_url("file:contracts/nft.py")


def make_metadata(symbol, name):
    """Helper function to build metadata JSON bytes values."""
    return sp.map(
        l={
            "name": sp.utils.bytes_of_string(name),
            "symbol": sp.utils.bytes_of_string(symbol),
        }
    )


def get_test_environment():
    # Initialize the test scenario
    scenario = sp.test_scenario()

    # Create the test accounts
    admin = sp.test_account("admin")
    user1 = sp.test_account("user1")
    user2 = sp.test_account("user2")
    user3 = sp.test_account("user3")

    # Initialize the extended FA2 contract
    fa2 = nft_module.NFT(
        administrator=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    )
    scenario += fa2

    # Save all the variables in a test environment dictionary
    return {
        "scenario": scenario,
        "admin": admin,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "fa2": fa2,
    }


@sp.add_test(name="Test Mint")
def test_mint_nft():
    test_env = get_test_environment()
    scenario = test_env["scenario"]
    admin = test_env["admin"]
    user1 = test_env["user1"]
    fa2 = test_env["fa2"]

    tok0_md = make_metadata(name="Cowboys SZN22", symbol="CBY22")

    scenario.h3("Mint from non-admin account")
    # Attempt to mint a token from a non-admin account and get an error
    fa2.mint([sp.record(metadata=tok0_md, to_=user1.address)]).run(
        sender=user1, valid=False, exception="FA2_NOT_ADMIN"
    )

    scenario.h3("Mint from admin account")
    # Mint of a new NFT token from a non-admin account
    fa2.mint([sp.record(metadata=tok0_md, to_=user1.address)]).run(sender=admin)

    scenario.verify(fa2.get_balance(sp.record(owner=user1.address, token_id=0)) == 1)
    scenario.verify(sp.len(fa2.all_tokens()) == 1)
    scenario.verify(fa2.token_metadata(0).token_info["name"] == tok0_md["name"])
    scenario.verify(fa2.token_metadata(0).token_info["symbol"] == tok0_md["symbol"])
    scenario.verify(~fa2.is_claimed(0))