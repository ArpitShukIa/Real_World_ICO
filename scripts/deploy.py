from brownie import chain, DappToken, DappTokenCrowdsale

from scripts.helpful_scripts import get_account, ether

CROWDSALE_RATE = 500
CAP = ether(100)
GOAL = ether(50)

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
    dapp_token.pause()
    dapp_token.transferOwnership(dapp_token_crowdsale)
    return dapp_token, dapp_token_crowdsale


def main():
    deploy()
