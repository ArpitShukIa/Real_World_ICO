from brownie import chain, DappToken, DappTokenCrowdsale
from web3 import Web3

from scripts.helpful_scripts import get_account

CROWDSALE_RATE = 500
CAP = Web3.toWei(100, 'ether')
GOAL = Web3.toWei(50, 'ether')

WEEK_IN_SECONDS = 7 * 24 * 60 * 60  # Seconds in 1 week


def deploy():
    account = get_account()
    wallet = get_account(index=1)
    opening_time = chain.time() + WEEK_IN_SECONDS
    closing_time = opening_time + WEEK_IN_SECONDS
    dapp_token = DappToken.deploy('Dapp Token', 'DAPP', 18, {'from': account})
    dapp_token_crowdsale = DappTokenCrowdsale.deploy(
        CROWDSALE_RATE, wallet, dapp_token, CAP, opening_time, closing_time, GOAL,
        {'from': account}
    )
    dapp_token.transferOwnership(dapp_token_crowdsale)
    return dapp_token, dapp_token_crowdsale


def main():
    deploy()
