import asyncio
import logging
from web3 import Web3
from app.core.config import settings

logger = logging.getLogger(__name__)

WALLET_ABI = [
    {
        "inputs": [],
        "name": "frozen",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "perTxLimit",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "periodLimit",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "spentThisPeriod",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "allowedTargets",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "target", "type": "address"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "name": "execute",
        "outputs": [],
        "stateMutability": "external",
        "type": "function"
    }
]

def get_web3_client() -> Web3:
    """Return a Web3 instance configured with the RPC provider URL."""
    return Web3(Web3.HTTPProvider(settings.RPC_PROVIDER_URL))

def get_contract(w3: Web3, contract_address: str = None):
    """Return the initialized contract instance if address is configured."""
    addr = contract_address or settings.SMART_CONTRACT_ADDRESS
    if not addr:
        raise ValueError("SMART_CONTRACT_ADDRESS is not set in environment settings.")
    checksum_addr = w3.to_checksum_address(addr)
    return w3.eth.contract(address=checksum_addr, abi=WALLET_ABI)

async def check_on_chain_status(contract_address: str = None) -> dict:
    """Read basic status fields from the contract."""
    try:
        w3 = get_web3_client()
        connected = await asyncio.to_thread(w3.is_connected)
        if not connected:
            return {"status": "disconnected", "error": "Unable to connect to RPC"}
            
        contract = get_contract(w3, contract_address)
        
        frozen = await asyncio.to_thread(contract.functions.frozen().call)
        per_tx = await asyncio.to_thread(contract.functions.perTxLimit().call)
        period = await asyncio.to_thread(contract.functions.periodLimit().call)
        spent = await asyncio.to_thread(contract.functions.spentThisPeriod().call)
        
        balance_wei = await asyncio.to_thread(w3.eth.get_balance, contract.address)
        
        return {
            "status": "connected",
            "frozen": frozen,
            "balance_wei": balance_wei,
            "balance_eth": float(w3.from_wei(balance_wei, 'ether')),
            "per_tx_limit_wei": per_tx,
            "period_limit_wei": period,
            "spent_this_period_wei": spent,
            "per_tx_limit_eth": float(w3.from_wei(per_tx, 'ether')),
            "period_limit_eth": float(w3.from_wei(period, 'ether')),
            "spent_this_period_eth": float(w3.from_wei(spent, 'ether')),
        }
    except Exception as e:
        logger.error(f"Failed to check on-chain status: {e}")
        return {"status": "error", "error": str(e)}

async def execute_on_chain_payment(target_address: str, amount_eth: float, contract_address: str = None) -> str:
    """Build, sign, and send execute() transaction using the AGENT_PRIVATE_KEY."""
    if not settings.AGENT_PRIVATE_KEY:
        raise ValueError("AGENT_PRIVATE_KEY is not set.")
        
    w3 = get_web3_client()
    connected = await asyncio.to_thread(w3.is_connected)
    if not connected:
        raise ConnectionError("Failed to connect to blockchain RPC node.")

    account = w3.eth.account.from_key(settings.AGENT_PRIVATE_KEY)
    agent_address = account.address

    contract = get_contract(w3, contract_address)
    target_checksum = w3.to_checksum_address(target_address)
    amount_wei = w3.to_wei(amount_eth, 'ether')

    logger.info(
        f"Preparing on-chain payment: agent={agent_address} contract={contract.address} "
        f"target={target_checksum} amount={amount_eth} ETH ({amount_wei} Wei)"
    )

    nonce = await asyncio.to_thread(w3.eth.get_transaction_count, agent_address)
    gas_price = await asyncio.to_thread(lambda: w3.eth.gas_price)
    chain_id = await asyncio.to_thread(lambda: w3.eth.chain_id)

    tx_data = await asyncio.to_thread(
        contract.functions.execute(
            target_checksum,
            amount_wei,
            b"" # Empty calldata for simple transfer
        ).build_transaction,
        {
            'chainId': chain_id,
            'gas': 200000,
            'gasPrice': gas_price,
            'nonce': nonce,
        }
    )

    signed_tx = w3.eth.account.sign_transaction(tx_data, private_key=settings.AGENT_PRIVATE_KEY)

    tx_hash = await asyncio.to_thread(w3.eth.send_raw_transaction, signed_tx.raw_transaction)
    logger.info(f"On-chain transaction broadcasted. Hash: {w3.to_hex(tx_hash)}")
    
    tx_receipt = await asyncio.to_thread(w3.eth.wait_for_transaction_receipt, tx_hash)

    if tx_receipt.status != 1:
        raise RuntimeError("On-chain transaction execution reverted.")

    tx_hash_hex = w3.to_hex(tx_hash)
    logger.info(f"On-chain payment successful: tx_hash={tx_hash_hex}")
    return tx_hash_hex
