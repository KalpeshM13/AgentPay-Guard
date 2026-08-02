const API_BASE_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

function getHeaders(extraHeaders = {}) {
  const headers = { ...extraHeaders };
  const token = localStorage.getItem("token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

export async function login(email, password) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Invalid email or password");
  }
  return response.json();
}

export async function register(email, password, displayName) {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email,
      password,
      display_name: displayName,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Registration failed");
  }
  return response.json();
}

export async function getMe() {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch user profile");
  }
  return response.json();
}

export async function getAgents() {
  const response = await fetch(`${API_BASE_URL}/agents`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch agents list");
  }
  return response.json();
}

export async function getAgent(id) {
  const response = await fetch(`${API_BASE_URL}/agents/${id}`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch agent details");
  }
  return response.json();
}

export async function getTransactions(id) {
  const response = await fetch(`${API_BASE_URL}/agents/${id}/transactions`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to fetch transaction history");
  }
  return response.json();
}

export async function freezeAgent(id) {
  const response = await fetch(`${API_BASE_URL}/agents/${id}/freeze`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to freeze agent");
  }
  return response.json();
}

export async function unfreezeAgent(id) {
  const response = await fetch(`${API_BASE_URL}/agents/${id}/unfreeze`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to unfreeze agent");
  }
  return response.json();
}

export async function updatePolicy(id, perTxLimit, dailyLimit) {
  const response = await fetch(`${API_BASE_URL}/agents/${id}/policy`, {
    method: "PUT",
    headers: getHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      per_transaction_limit: parseFloat(perTxLimit), // Note: updated to match backend field name
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
  const response = await fetch(`${API_BASE_URL}/agents/${id}/allowlist`, {
    method: "POST",
    headers: getHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify({
      merchant_id: parseInt(merchantId),
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
  const response = await fetch(
    `${API_BASE_URL}/agents/${id}/allowlist/${merchantId}`,
    {
      method: "DELETE",
      headers: getHeaders(),
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
