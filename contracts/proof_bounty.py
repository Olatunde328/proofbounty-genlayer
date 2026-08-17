# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from genlayer import *


@allow_storage
@dataclass
class Bounty:
    id: str
    creator: Address
    contributor: Address
    title: str
    requirements: str
    evidence_url: str
    status: str
    verdict: str
    reasoning: str
    reward: u256
    paid: bool


@gl.evm.contract_interface
class _Recipient:
    class View:
        pass

    class Write:
        pass


class ProofBounty(gl.Contract):
    bounties: TreeMap[str, Bounty]
    bounty_count: u256

    def __init__(self):
        self.bounty_count = 0

    def _evaluate_evidence(
        self,
        title: str,
        requirements: str,
        evidence_url: str,
    ) -> dict:

        def evaluate() -> str:
            web_data = gl.nondet.web.render(
                evidence_url,
                mode="text",
            )

            task = f"""
You are evaluating evidence submitted for a Web3 bounty.

BOUNTY TITLE:
{title}

BOUNTY REQUIREMENTS:
{requirements}

SUBMITTED EVIDENCE URL:
{evidence_url}

CONTENT RETRIEVED FROM THE EVIDENCE:
{web_data}

Determine whether the submitted evidence satisfies the bounty requirements.

Be strict and evidence-based.

Do not assume that something was completed unless the retrieved evidence
supports it.

Respond ONLY with valid JSON in exactly this structure:

{{
    "verdict": "PASS" or "FAIL",
    "reasoning": "A concise explanation of why the evidence passes or fails"
}}

Do not include markdown.
Do not include text outside the JSON object.
"""

            result = gl.nondet.exec_prompt(
                task,
                response_format="json",
            )

            return json.dumps(result, sort_keys=True)

        result_json = json.loads(
            gl.eq_principle.strict_eq(evaluate)
        )

        return result_json

    @gl.public.write.payable
    def create_bounty(
        self,
        title: str,
        requirements: str,
    ) -> None:

        if not title.strip():
            raise gl.vm.UserError("Title is required")

        if not requirements.strip():
            raise gl.vm.UserError("Requirements are required")

        sender = gl.message.sender_address
        reward = gl.message.value

        if reward == u256(0):
            raise gl.vm.UserError("Bounty reward is required")

        bounty_id = f"bounty-{int(self.bounty_count) + 1}"

        bounty = Bounty(
            id=bounty_id,
            creator=sender,
            contributor=Address("0x0000000000000000000000000000000000000000"),
            title=title,
            requirements=requirements,
            evidence_url="",
            status="OPEN",
            verdict="",
            reasoning="",
            reward=reward,
            paid=False,
        )

        self.bounties[bounty_id] = bounty
        self.bounty_count += 1

    @gl.public.write
    def accept_bounty(self, bounty_id: str) -> None:

        if bounty_id not in self.bounties:
            raise gl.vm.UserError("Bounty not found")

        bounty = self.bounties[bounty_id]

        if bounty.status != "OPEN":
            raise gl.vm.UserError("Bounty is not open")

        if gl.message.sender_address == bounty.creator:
            raise gl.vm.UserError("Creator cannot accept own bounty")

        bounty.contributor = gl.message.sender_address
        bounty.status = "IN_PROGRESS"

    @gl.public.write
    def submit_evidence(
        self,
        bounty_id: str,
        evidence_url: str,
    ) -> None:

        if bounty_id not in self.bounties:
            raise gl.vm.UserError("Bounty not found")

        bounty = self.bounties[bounty_id]

        if bounty.status != "IN_PROGRESS":
            raise gl.vm.UserError("Bounty is not in progress")

        if gl.message.sender_address != bounty.contributor:
            raise gl.vm.UserError("Only contributor can submit evidence")

        if not evidence_url.strip():
            raise gl.vm.UserError("Evidence URL is required")

        if not (
            evidence_url.startswith("https://")
            or evidence_url.startswith("http://")
        ):
            raise gl.vm.UserError("Evidence must be a web URL")

        bounty.evidence_url = evidence_url
        bounty.status = "SUBMITTED"

    @gl.public.write
    def evaluate_submission(self, bounty_id: str) -> None:

        if bounty_id not in self.bounties:
            raise gl.vm.UserError("Bounty not found")

        bounty = self.bounties[bounty_id]

        if bounty.status != "SUBMITTED":
            raise gl.vm.UserError("Bounty has no submission to evaluate")

        result = self._evaluate_evidence(
            bounty.title,
            bounty.requirements,
            bounty.evidence_url,
        )

        verdict = str(result["verdict"]).upper()
        reasoning = str(result["reasoning"])

        if verdict not in ("PASS", "FAIL"):
            raise gl.vm.UserError("Invalid evaluation verdict")

        bounty.verdict = verdict
        bounty.reasoning = reasoning

        if verdict == "PASS":
            bounty.status = "APPROVED"

            if bounty.paid:
                raise gl.vm.UserError("Bounty already paid")

            _Recipient(bounty.contributor).emit_transfer(
                value=bounty.reward
            )

            bounty.paid = True
        else:
            bounty.status = "REJECTED"

    @gl.public.view
    def get_bounty(self, bounty_id: str) -> Bounty:

        if bounty_id not in self.bounties:
            raise gl.vm.UserError("Bounty not found")

        return self.bounties[bounty_id]

    @gl.public.view
    def get_bounties(self) -> dict:
        return {
            bounty_id: bounty
            for bounty_id, bounty in self.bounties.items()
        }

    @gl.public.view
    def get_bounty_count(self) -> int:
        return int(self.bounty_count)
