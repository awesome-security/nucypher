"""
This file is part of nucypher.

nucypher is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

nucypher is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with nucypher.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import pytest
from eth_utils import keccak

from nucypher.blockchain.eth.agents import AdjudicatorAgent
from nucypher.blockchain.eth.deployers import (
    AdjudicatorDeployer,
    NucypherTokenDeployer,
    StakingEscrowDeployer,
    DispatcherDeployer
)


@pytest.mark.slow()
def test_adjudicator_deployer(testerchain, slashing_economics):
    origin = testerchain.etherbase_account

    token_deployer = NucypherTokenDeployer(blockchain=testerchain, deployer_address=origin)
    token_deployer.deploy()

    stakers_escrow_secret = os.urandom(DispatcherDeployer.DISPATCHER_SECRET_LENGTH)
    staking_escrow_deployer = StakingEscrowDeployer(deployer_address=origin, blockchain=testerchain)

    staking_escrow_deployer.deploy(secret_hash=keccak(stakers_escrow_secret))
    staking_agent = staking_escrow_deployer.make_agent()  # 2 Staker Escrow

    deployer = AdjudicatorDeployer(deployer_address=origin, blockchain=testerchain)
    deployment_txhashes = deployer.deploy(secret_hash=os.urandom(DispatcherDeployer.DISPATCHER_SECRET_LENGTH))

    assert len(deployment_txhashes) == 3

    for title, txhash in deployment_txhashes.items():
        receipt = testerchain.wait_for_receipt(txhash=txhash)
        assert receipt['status'] == 1, "Transaction Rejected {}:{}".format(title, txhash)

    # Create an AdjudicatorAgent instance
    adjudicator_agent = deployer.make_agent()

    # Check default Adjudicator deployment parameters
    assert adjudicator_agent.staking_escrow_contract == staking_agent.contract_address
    assert adjudicator_agent.hash_algorithm == slashing_economics.hash_algorithm
    assert adjudicator_agent.base_penalty == slashing_economics.base_penalty
    assert adjudicator_agent.penalty_history_coefficient == slashing_economics.penalty_history_coefficient
    assert adjudicator_agent.percentage_penalty_coefficient == slashing_economics.percentage_penalty_coefficient
    assert adjudicator_agent.reward_coefficient == slashing_economics.reward_coefficient

    # Retrieve the AdjudicatorAgent singleton
    some_policy_agent = AdjudicatorAgent()
    assert adjudicator_agent == some_policy_agent  # __eq__

    # Compare the contract address for equality
    assert adjudicator_agent.contract_address == some_policy_agent.contract_address
