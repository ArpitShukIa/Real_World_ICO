import pytest
from brownie import exceptions, chain, web3, project, config, DappToken, Contract
from web3 import Web3

from scripts.deploy import deploy, CROWDSALE_RATE, WEEK_IN_SECONDS
from scripts.helpful_scripts import get_account, ether

INVESTOR_MIN_CAP = ether(0.002)
INVESTOR_HARD_CAP = ether(50)
PRE_ICO_STAGE = 0
ICO_STAGE = 1
PRE_ICO_RATE = 500
ICO_RATE = 250

RefundVault = project.load(config["dependencies"][0]).RefundVault


@pytest.fixture
def dapp_token_crowdsale():
    investor1, investor2 = get_account(index=2), get_account(index=3)
    _, dapp_token_crowdsale = deploy()
    chain.sleep(WEEK_IN_SECONDS)
    dapp_token_crowdsale.addManyToWhitelist([investor1, investor2])
    return dapp_token_crowdsale


@pytest.fixture
def dapp_token(dapp_token_crowdsale):
    dapp_token_address = dapp_token_crowdsale.token()
    return Contract.from_abi('DappToken', dapp_token_address, DappToken.abi)


def test_contracts_deployed_correctly(dapp_token, dapp_token_crowdsale):
    wallet = get_account(index=1)
    assert dapp_token.name() == 'Dapp Token'
    assert dapp_token.symbol() == 'DAPP'
    assert dapp_token.decimals() == 18
    assert dapp_token_crowdsale.rate() == CROWDSALE_RATE
    assert dapp_token_crowdsale.wallet() == wallet
    assert dapp_token_crowdsale.token() == dapp_token


def test_crowdsale_accepts_payment(dapp_token_crowdsale):
    value = Web3.toWei(1, "ether")
    investor = get_account(index=2)
    purchaser = get_account(index=3)
    dapp_token_crowdsale.buyTokens(investor, {'from': purchaser, 'value': value})


def test_buy_tokens(dapp_token_crowdsale):
    investor = get_account(index=2)

    # when the contribution is less than the minimum cap
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': INVESTOR_MIN_CAP - 1})

    # when the investor has already met the minimum cap
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(2)})
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(49)})

    assert dapp_token_crowdsale.getUserContribution(investor) == ether(2)


def test_non_whitelisted_cannot_buy_tokens(dapp_token_crowdsale):
    investor = get_account(index=0)
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': INVESTOR_MIN_CAP})


def test_crowdsale_stage_and_rate(dapp_token_crowdsale):
    owner = get_account()
    investor = get_account(index=2)

    assert dapp_token_crowdsale.stage() == PRE_ICO_STAGE
    assert dapp_token_crowdsale.rate() == PRE_ICO_RATE

    # non owner can not change crowdsale stage
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.setCrowdsaleStage(ICO_STAGE, {'from': investor})

    dapp_token_crowdsale.setCrowdsaleStage(ICO_STAGE, {'from': owner})
    assert dapp_token_crowdsale.stage() == ICO_STAGE
    assert dapp_token_crowdsale.rate() == ICO_RATE


def test_cannot_claim_refund_during_crowdsale(dapp_token_crowdsale):
    investor = get_account(index=2)
    refund_vault = RefundVault.at(dapp_token_crowdsale.vault())
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(1)})
    with pytest.raises(exceptions.VirtualMachineError):
        refund_vault.refund(investor, {'from': investor})


def test_ether_is_sent_to_correct_account(dapp_token_crowdsale):
    owner = get_account()
    wallet = get_account(index=1)
    investor = get_account(index=2)
    refund_vault = RefundVault.at(dapp_token_crowdsale.vault())

    initial_wallet_balance = wallet.balance()

    # verify that ether is sent to wallet in PRE_ICO stage
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(1)})
    assert wallet.balance() == initial_wallet_balance + ether(1)

    # verify that ether is sent to refund vault in ICO stage
    dapp_token_crowdsale.setCrowdsaleStage(ICO_STAGE, {'from': owner})
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(1)})
    assert refund_vault.balance() == ether(1)


def test_token_transfer_not_allowed_during_crowdsale(dapp_token, dapp_token_crowdsale):
    investor1 = get_account(index=2)
    investor2 = get_account(index=3)
    dapp_token_crowdsale.buyTokens(investor1, {'from': investor1, 'value': ether(1)})

    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token.transfer(investor2, 1, {'from': investor1})


def test_finalizing_crowdsale_when_goal_not_reached(dapp_token_crowdsale):
    owner = get_account()
    investor = get_account(index=2)
    refund_vault_address = dapp_token_crowdsale.vault()
    refund_vault = RefundVault.at(refund_vault_address)

    # Do not meet the goal
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(1)})
    # Fastforward past end time
    chain.sleep(WEEK_IN_SECONDS + 1)
    # Finalize the crowdsale
    dapp_token_crowdsale.finalize({'from': owner})

    # Verify that claiming refund is allowed
    refund_vault.refund(investor, {'from': investor})


def test_finalizing_crowdsale_when_goal_reached(dapp_token, dapp_token_crowdsale):
    owner = get_account()
    investor1 = get_account(index=2)
    investor2 = get_account(index=3)
    refund_vault_address = dapp_token_crowdsale.vault()
    refund_vault = RefundVault.at(refund_vault_address)

    # Meet the goal
    dapp_token_crowdsale.buyTokens(investor1, {'from': investor1, 'value': ether(50)})
    # Fastforward past end time
    chain.sleep(WEEK_IN_SECONDS + 1)
    # Finalize the crowdsale
    dapp_token_crowdsale.finalize({'from': owner})

    assert dapp_token_crowdsale.goalReached()
    assert dapp_token.mintingFinished()
    assert not dapp_token.paused()

    # Verify that token transfer is now allowed
    dapp_token.transfer(investor2, 1, {'from': investor1})

    # Verify that claiming refund is not allowed
    with pytest.raises(exceptions.VirtualMachineError):
        refund_vault.refund(investor1, {'from': investor1})
