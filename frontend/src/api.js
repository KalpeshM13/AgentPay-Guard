const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

function getHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const walletAddress = localStorage.getItem("walletAddress");
  if (walletAddress) {
    headers["X-Wallet-Address"] = walletAddress;
  }
  return headers;
}

async function apiFetch(url, options = {}) {
  const headers = getHeaders(options.headers);
  return await fetch(url, { ...options, headers });
}


export async function getAgents() {
  const response = await apiFetch(`${API_BASE_URL}/agents`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch agents list");
  }
  return response.json();
}

export async function getAgent(id) {
  const response = await apiFetch(`${API_BASE_URL}/agents/${id}`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch agent details");
  }
  return response.json();
}

export async function getTransactions(id) {
  const response = await apiFetch(`${API_BASE_URL}/agents/${id}/transactions`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch transaction history");
  }
  return response.json();
}

export async function freezeAgent(id) {
  const response = await apiFetch(`${API_BASE_URL}/agents/${id}/freeze`, {
    method: "POST",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to freeze agent");
  }
  return response.json();
}

export async function unfreezeAgent(id) {
  const response = await apiFetch(`${API_BASE_URL}/agents/${id}/unfreeze`, {
    method: "POST",
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to unfreeze agent");
  }
  return response.json();
}

export async function updatePolicy(id, perTxLimit, dailyLimit) {
  const response = await apiFetch(`${API_BASE_URL}/agents/${id}/policy`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      per_transaction_limit: parseFloat(perTxLimit),
      daily_limit: parseFloat(dailyLimit),
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update policy");
  }
  return response.json();
}

export async function addToAllowlist(
  id,
  merchantId,
  displayName = null,
  destinationReference = null,
) {
  const parsedId = parseInt(merchantId);
  const response = await apiFetch(`${API_BASE_URL}/agents/${id}/allowlist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      merchant_id: isNaN(parsedId) ? null : parsedId,
      display_name: displayName,
      destination_reference: destinationReference,
    }),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to add merchant to allowlist");
  }
  return response.json();
}

export async function removeFromAllowlist(id, merchantId) {
  const response = await apiFetch(
    `${API_BASE_URL}/agents/${id}/allowlist/${merchantId}`,
    {
      method: "DELETE",
    },
  );
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(
      errorData.detail || "Failed to remove merchant from allowlist",
    );
  }
  return response.json();
}

export async function requestPayment(requestId, agentId, merchantId, amount) {
  const response = await fetch(`${API_BASE_URL}/payments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      request_id: requestId,
      agent_id: parseInt(agentId),
      merchant_id: parseInt(merchantId),
      amount: parseFloat(amount),
    }),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(
      data.detail?.reason || data.detail || "Payment request failed",
    );
  }
  return data;
}
