import pytest
from brownie import exceptions, chain
from web3 import Web3

from scripts.deploy import deploy, CROWDSALE_RATE, WEEK_IN_SECONDS
from scripts.helpful_scripts import get_account

INVESTOR_MIN_CAP = Web3.toWei(0.002, 'ether')
INVESTOR_HARD_CAP = Web3.toWei(50, 'ether')


@pytest.fixture
def contracts():
    investor1, investor2 = get_account(index=1), get_account(index=2)
    dapp_token, dapp_token_crowdsale = deploy()
    chain.sleep(WEEK_IN_SECONDS)
    dapp_token_crowdsale.addManyToWhitelist([investor1, investor2])
    return dapp_token, dapp_token_crowdsale


def test_contracts_deployed_correctly(contracts):
    wallet = get_account(index=1)
    dapp_token, dapp_token_crowdsale = contracts
    assert dapp_token.name() == 'Dapp Token'
    assert dapp_token.symbol() == 'DAPP'
    assert dapp_token.decimals() == 18
    assert dapp_token_crowdsale.rate() == CROWDSALE_RATE
    assert dapp_token_crowdsale.wallet() == wallet
    assert dapp_token_crowdsale.token() == dapp_token


def test_crowdsale_accepts_payment(contracts):
    value = Web3.toWei(1, "ether")
    investor = get_account(index=2)
    purchaser = get_account(index=3)
    dapp_token, dapp_token_crowdsale = contracts
    dapp_token_crowdsale.buyTokens(investor, {'from': purchaser, 'value': value})


def test_buy_tokens(contracts):
    investor = get_account(index=2)
    dapp_token, dapp_token_crowdsale = contracts

    # when the contribution is less than the minimum cap
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': INVESTOR_MIN_CAP - 1})

    # when the investor has already met the minimum cap
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': Web3.toWei(2, 'ether')})
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': Web3.toWei(49, 'ether')})

    assert dapp_token_crowdsale.getUserContribution(investor) == Web3.toWei(2, 'ether')


def test_non_whitelisted_cannot_buy_tokens(contracts):
    investor = get_account(index=0)
    dapp_token, dapp_token_crowdsale = contracts
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': INVESTOR_MIN_CAP})
