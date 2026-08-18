"""Direct tests for the ProofBounty Intelligent Contract."""

import json

from tests.direct.conftest import to_hex


TEST_REWARD = 10**18  # 1 GEN in wei


def _setup_evaluation_mocks(
    vm,
    verdict="PASS",
    reasoning="Requirements satisfied",
):
    """Mock web evidence and GenLayer LLM evaluation."""

    vm.mock_web(
        r".*example\.com.*",
        {
            "status": 200,
            "body": (
                "Project: GenLayer Landing Page. "
                "Status: completed. "
                "Responsive layout included. "
                "Public GitHub repository included. "
                "Wallet connect implemented. "
                "README documentation included."
            ),
        },
    )

    vm.mock_llm(
        r".*evaluating evidence submitted for a Web3 bounty.*",
        json.dumps(
            {
                "verdict": verdict,
                "reasoning": reasoning,
            }
        ),
    )


def test_create_bounty(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    alice = to_hex(direct_alice)

    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build a GenLayer landing page",
        "Must be responsive and include a public GitHub repository",
    )

    bounty = contract.get_bounty("bounty-1")

    assert bounty["id"] == "bounty-1"
    assert bounty["creator"] == alice
    assert bounty["title"] == "Build a GenLayer landing page"
    assert bounty["status"] == "OPEN"
    assert bounty["evidence_url"] == ""
    assert bounty["verdict"] == ""
    assert contract.get_bounty_count() == 1


def test_creator_cannot_accept_own_bounty(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice

    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build landing page",
        "Must be responsive",
    )

    with direct_vm.expect_revert(
        "Creator cannot accept own bounty"
    ):
        contract.accept_bounty("bounty-1")


def test_contributor_can_accept_bounty(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice

    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build landing page",
        "Must be responsive",
    )

    direct_vm.sender = direct_bob
    bob = to_hex(direct_bob)

    contract.accept_bounty("bounty-1")

    bounty = contract.get_bounty("bounty-1")

    assert bounty["status"] == "IN_PROGRESS"
    assert bounty["contributor"] == bob


def test_submit_evidence(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice

    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build landing page",
        "Must be responsive",
    )

    direct_vm.sender = direct_bob
    contract.accept_bounty("bounty-1")

    contract.submit_evidence(
        "bounty-1",
        "https://example.com/project",
    )

    bounty = contract.get_bounty("bounty-1")

    assert bounty["status"] == "SUBMITTED"
    assert bounty["evidence_url"] == "https://example.com/project"


def test_only_contributor_can_submit_evidence(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
    direct_charlie,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build landing page",
        "Must be responsive",
    )

    direct_vm.sender = direct_bob
    contract.accept_bounty("bounty-1")

    direct_vm.sender = direct_charlie

    with direct_vm.expect_revert(
        "Only contributor can submit evidence"
    ):
        contract.submit_evidence(
            "bounty-1",
            "https://example.com/project",
        )


def test_invalid_evidence_url_rejected(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build landing page",
        "Must be responsive",
    )

    direct_vm.sender = direct_bob
    contract.accept_bounty("bounty-1")

    with direct_vm.expect_revert(
        "Evidence must be a web URL"
    ):
        contract.submit_evidence(
            "bounty-1",
            "example.com/project",
        )


def test_evaluation_passes_valid_submission(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build a GenLayer landing page",
        "Must be responsive and include a public GitHub repository",
    )

    direct_vm.sender = direct_bob
    contract.accept_bounty("bounty-1")

    contract.submit_evidence(
        "bounty-1",
        "https://example.com/project",
    )

    _setup_evaluation_mocks(
        direct_vm,
        verdict="PASS",
        reasoning="The evidence satisfies the required criteria.",
    )

    contract.evaluate_submission("bounty-1")

    bounty = contract.get_bounty("bounty-1")

    assert bounty["status"] == "APPROVED"
    assert bounty["verdict"] == "PASS"
    assert (
        bounty["reasoning"]
        == "The evidence satisfies the required criteria."
    )


def test_evaluation_rejects_invalid_submission(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build a GenLayer landing page",
        "Must include wallet connect and documentation",
    )

    direct_vm.sender = direct_bob
    contract.accept_bounty("bounty-1")

    contract.submit_evidence(
        "bounty-1",
        "https://example.com/project",
    )

    _setup_evaluation_mocks(
        direct_vm,
        verdict="FAIL",
        reasoning="The evidence does not prove wallet connectivity.",
    )

    contract.evaluate_submission("bounty-1")

    bounty = contract.get_bounty("bounty-1")

    assert bounty["status"] == "REJECTED"
    assert bounty["verdict"] == "FAIL"
    assert (
        bounty["reasoning"]
        == "The evidence does not prove wallet connectivity."
    )


def test_cannot_evaluate_twice(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD
    contract.create_bounty(
        "Build landing page",
        "Must be responsive",
    )

    direct_vm.sender = direct_bob
    contract.accept_bounty("bounty-1")

    contract.submit_evidence(
        "bounty-1",
        "https://example.com/project",
    )

    _setup_evaluation_mocks(direct_vm)

    contract.evaluate_submission("bounty-1")

    with direct_vm.expect_revert(
        "Bounty has no submission to evaluate"
    ):
        contract.evaluate_submission("bounty-1")


def test_zero_reward_bounty_rejected(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = 0

    with direct_vm.expect_revert(
        "Bounty reward is required"
    ):
        contract.create_bounty(
            "Unfunded bounty",
            "Must not be created without escrow",
        )


def test_bounty_stores_reward(
    direct_vm,
    direct_deploy,
    direct_alice,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD

    contract.create_bounty(
        "Build an escrowed landing page",
        "Must provide a live deployment",
    )

    bounty = contract.get_bounty("bounty-1")

    assert int(bounty["reward"]) == TEST_REWARD
    assert bounty["paid"] is False


def test_failed_submission_keeps_escrow_unpaid(
    direct_vm,
    direct_deploy,
    direct_alice,
    direct_bob,
):
    contract = direct_deploy("contracts/proof_bounty.py")

    direct_vm.sender = direct_alice
    direct_vm.value = TEST_REWARD

    contract.create_bounty(
        "Build a wallet-enabled app",
        "Must demonstrate working wallet connection",
    )

    direct_vm.sender = direct_bob
    direct_vm.value = 0

    contract.accept_bounty("bounty-1")

    contract.submit_evidence(
        "bounty-1",
        "https://example.com/project",
    )

    _setup_evaluation_mocks(
        direct_vm,
        verdict="FAIL",
        reasoning="Wallet functionality was not demonstrated.",
    )

    contract.evaluate_submission("bounty-1")

    bounty = contract.get_bounty("bounty-1")

    assert bounty["status"] == "REJECTED"
    assert bounty["verdict"] == "FAIL"
    assert bounty["paid"] is False
    assert int(bounty["reward"]) == TEST_REWARD
