from brownie import chain, network, config, DappToken, DappTokenCrowdsale

from scripts.helpful_scripts import get_account, ether, LOCAL_BLOCKCHAIN_ENVIRONMENTS

CROWDSALE_RATE = 500
CAP = ether(100)
GOAL = ether(50)

WEEK_IN_SECONDS = 7 * 24 * 60 * 60  # Seconds in 1 week
YEAR_IN_SECONDS = 365 * 24 * 60 * 60  # Seconds in 1 year


def deploy_dapp_token():
    account = get_account()
    dapp_token = DappToken.deploy(
        'Dapp Token', 'DAPP', 18,
        {'from': account},
        publish_source=config["networks"][network.show_active()].get("verify", False)
    )
    return dapp_token


def deploy_dapp_token_crowdsale(dapp_token):
    owner = get_account()
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        wallet = get_account(index=1)
        founders_fund = get_account(index=4)
        foundation_fund = get_account(index=5)
        partners_fund = get_account(index=6)
    else:
        # TODO: Use different accounts here
        wallet = owner
        founders_fund = owner
        foundation_fund = owner
        partners_fund = owner

    opening_time = chain.time() + WEEK_IN_SECONDS
    closing_time = opening_time + WEEK_IN_SECONDS
    release_time = closing_time + YEAR_IN_SECONDS
    dapp_token_crowdsale = DappTokenCrowdsale.deploy(
        CROWDSALE_RATE, wallet, dapp_token, CAP, opening_time, closing_time, GOAL,
        founders_fund, foundation_fund, partners_fund, release_time,
        {'from': owner},
        publish_source=config["networks"][network.show_active()].get("verify", False)
    )
    dapp_token.pause()
    dapp_token.transferOwnership(dapp_token_crowdsale)
    return dapp_token_crowdsale


def main():
    dapp_token = deploy_dapp_token()
    deploy_dapp_token_crowdsale(dapp_token)
