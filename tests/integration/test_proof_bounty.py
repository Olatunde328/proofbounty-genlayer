"""ProofBounty integration tests against GLSim / GenLayer Studio."""

import pytest

from gltest import get_contract_factory, get_accounts
from gltest.assertions import tx_execution_succeeded


TEST_REWARD = 10**18  # 1 GEN


@pytest.mark.integration
def test_proof_bounty_funded_multi_account_lifecycle():
    accounts = get_accounts()

    assert len(accounts) >= 2, (
        "ProofBounty integration test requires at least two configured accounts"
    )

    alice = accounts[0]
    bob = accounts[1]

    factory = get_contract_factory("ProofBounty")

    # Alice deploys the Intelligent Contract.
    contract = factory.deploy(
        account=alice,
        wait_retries=50,
    )

    alice_contract = contract.connect(alice)
    bob_contract = contract.connect(bob)

    # Alice creates the bounty and escrows 1 GEN.
    create_tx = alice_contract.create_bounty(
        args=[
            "Build a GenLayer landing page",
            (
                "Create a responsive landing page with a public "
                "GitHub repository and documentation."
            ),
        ],
    ).transact(
        value=TEST_REWARD,
        wait_retries=50,
    )

    if not tx_execution_succeeded(create_tx):
        print("\n=== CREATE BOUNTY RECEIPT ===")
        print(create_tx)

    assert tx_execution_succeeded(create_tx)

    bounty = contract.get_bounty(
        args=["bounty-1"]
    ).call()

    assert bounty["id"] == "bounty-1"
    assert bounty["status"] == "OPEN"
    assert int(bounty["reward"]) == TEST_REWARD
    assert bounty["paid"] is False

    # Bob accepts the bounty.
    accept_tx = bob_contract.accept_bounty(
        args=["bounty-1"]
    ).transact(
        wait_retries=50,
    )

    assert tx_execution_succeeded(accept_tx)

    bounty = contract.get_bounty(
        args=["bounty-1"]
    ).call()

    assert bounty["status"] == "IN_PROGRESS"
    assert bounty["contributor"].lower() == bob.address.lower()

    # Bob submits web evidence.
    submit_tx = bob_contract.submit_evidence(
        args=[
            "bounty-1",
            "https://example.com/proofbounty-demo",
        ],
    ).transact(
        wait_retries=50,
    )

    assert tx_execution_succeeded(submit_tx)

    bounty = contract.get_bounty(
        args=["bounty-1"]
    ).call()

    assert bounty["status"] == "SUBMITTED"
    assert (
        bounty["evidence_url"]
        == "https://example.com/proofbounty-demo"
    )
    assert bounty["paid"] is False
