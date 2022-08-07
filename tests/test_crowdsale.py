import pytest
from brownie import exceptions, chain, web3
from web3 import Web3

from scripts.deploy import deploy, CROWDSALE_RATE, WEEK_IN_SECONDS
from scripts.helpful_scripts import get_account, ether

INVESTOR_MIN_CAP = ether(0.002)
INVESTOR_HARD_CAP = ether(50)
PRE_ICO_STAGE = 0
ICO_STAGE = 1
PRE_ICO_RATE = 500
ICO_RATE = 250


@pytest.fixture
def contracts():
    investor1, investor2 = get_account(index=2), get_account(index=3)
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
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(2)})
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(49)})

    assert dapp_token_crowdsale.getUserContribution(investor) == ether(2)


def test_non_whitelisted_cannot_buy_tokens(contracts):
    investor = get_account(index=0)
    dapp_token, dapp_token_crowdsale = contracts
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': INVESTOR_MIN_CAP})


def test_crowdsale_stage_and_rate(contracts):
    owner = get_account()
    investor = get_account(index=2)
    dapp_token, dapp_token_crowdsale = contracts

    assert dapp_token_crowdsale.stage() == PRE_ICO_STAGE
    assert dapp_token_crowdsale.rate() == PRE_ICO_RATE

    # non owner can not change crowdsale stage
    with pytest.raises(exceptions.VirtualMachineError):
        dapp_token_crowdsale.setCrowdsaleStage(ICO_STAGE, {'from': investor})

    dapp_token_crowdsale.setCrowdsaleStage(ICO_STAGE, {'from': owner})
    assert dapp_token_crowdsale.stage() == ICO_STAGE
    assert dapp_token_crowdsale.rate() == ICO_RATE


def test_ether_is_sent_to_correct_account(contracts):
    owner = get_account()
    wallet = get_account(index=1)
    investor = get_account(index=2)
    dapp_token, dapp_token_crowdsale = contracts
    refund_vault = dapp_token_crowdsale.vault()

    initial_wallet_balance = wallet.balance()

    # verify that ether is sent to wallet in PRE_ICO stage
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(1)})
    assert wallet.balance() == initial_wallet_balance + ether(1)

    # verify that ether is sent to refund vault in ICO stage
    dapp_token_crowdsale.setCrowdsaleStage(ICO_STAGE, {'from': owner})
    dapp_token_crowdsale.buyTokens(investor, {'from': investor, 'value': ether(1)})
    assert web3.eth.get_balance(refund_vault) == ether(1)
