try:
    from web3 import Web3
except Exception:
    Web3 = None


# Simulate Ethereum blockchain (local Ganache or Infura)
WEB3_PROVIDER = "http://127.0.0.1:7545"  # Ganache default


def _stub_send_payout(wallet_address: str, amount: float):
    # Fallback when web3/provider is not available — do not fail app startup
    print("[blockchain] web3 not available or provider not connected; using stub send_payout")
    return {
        "status": "stub",
        "wallet": wallet_address,
        "amount": amount,
        "txn_hash": "0xstub"
    }


if Web3 is None:
    send_payout = _stub_send_payout
else:
    w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))
    if not w3.isConnected():
        # If provider not connected, use stub but do not raise to prevent startup failure
        send_payout = _stub_send_payout
    else:
        # Dummy smart contract ABI & address (replace with real ones)
        DUMMY_CONTRACT_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"
        DUMMY_CONTRACT_ABI = []

        def send_payout(wallet_address: str, amount: float):
            """
            Simulate sending amount to wallet_address via smart contract
            """
            # For real deployment, call contract function like:
            # contract = w3.eth.contract(address=DUMMY_CONTRACT_ADDRESS, abi=DUMMY_CONTRACT_ABI)
            # tx_hash = contract.functions.transfer(wallet_address, amount).transact({'from': PLATFORM_ADDRESS})
            # Simulate success
            return {
                "status": "success",
                "wallet": wallet_address,
                "amount": amount,
                "txn_hash": "0xdummytransactionhash123"
            }
