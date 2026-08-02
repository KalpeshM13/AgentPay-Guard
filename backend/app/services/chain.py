import subprocess
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "0x5FbDB2315678afecb367f032d93F642f64180aa3")
RPC_URL = os.getenv("RPC_URL", "http://127.0.0.1:8545")

def execute_payment(target: str, amount_wei: int, data: bytes, agent_key: str) -> str:
    """Send an execute transaction using a Node.js script (to bypass Windows web3.py compilation issues)."""
    script_path = os.path.join(os.path.dirname(__dirname), "..", "execute.js")
    
    try:
        result = subprocess.run(
            ["node", script_path, target, str(amount_wei), agent_key, CONTRACT_ADDRESS, RPC_URL],
            capture_output=True,
            text=True,
            check=True
        )
        tx_hash = result.stdout.strip()
        return tx_hash
    except subprocess.CalledProcessError as e:
        logger.error(f"Blockchain execution failed via Node: {e.stderr}")
        raise RuntimeError(f"Smart Contract reverted or execution failed: {e.stderr}")
