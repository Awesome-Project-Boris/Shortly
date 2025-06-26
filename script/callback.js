document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get("code");
  if (!code) {
    console.error("Authorization code not found in URL.");
    return;
  }

  // Configuration variables - These should be dynamically injected or configured
  const clientId = "7tln9sb8nkvncp4mlb9vagobeu";
  // const clientSecret = "11r9ns6ois9nd6toqr5p282hacitadajucnvc29loc55af1m6nb4"; // FIX: Removed client secret for a public client
  const redirectUri = "https://lior19-shortly-rlt.s3.us-east-1.amazonaws.com/main/callback.html";
  const tokenEndpoint = "https://lior19-us-east-1zsxqwhoz7.auth.us-east-1.amazoncognito.com/oauth2/token";
  const API = "https://9hvm0tpqoi.execute-api.us-east-1.amazonaws.com/lior19"; // Your API Gateway base URL

  // const basicAuth = btoa(`${clientId}:${clientSecret}`); // FIX: Removed as it's not needed for a public client

  try {
    // --- Step 1: Exchange Cognito code for tokens ---
    const response = await fetch(tokenEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        // FIX: Authorization header is not sent for a public client
      },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: clientId,
        redirect_uri: redirectUri,
        code: code,
      }),
    });

    const tokens = await response.json();
    if (!response.ok) {
      console.error("Token exchange failed:", tokens);
      throw new Error(`Token exchange failed with status: ${response.statusText}`);
    }

    const idToken = tokens.id_token;
    const payload = JSON.parse(atob(idToken.split(".")[1]));
    const uuid = payload.sub;

    localStorage.setItem("UserId", uuid);

    // --- Step 2: Check admin status ---
    const isAdminResp = await fetch(`${API}/users/is-user-admin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ UserId: uuid })
    });

    if (!isAdminResp.ok) {
      console.warn("Could not determine admin status. Defaulting to non-admin.");
      localStorage.setItem("isAdmin", false);
    } else {
      const isAdminBody = await isAdminResp.json();
      const isAdmin = isAdminBody.isAdmin === true;
      localStorage.setItem("isAdmin", isAdmin);
    }

    // --- Step 3: Redirect into the application ---
    window.location.href = "index.html";

  } catch (error) {
    console.error("Callback error:", error);
    const container = document.querySelector('.spinner-container');
    if (container) {
      container.innerHTML = `<p class="loading-message text-danger">Login failed. Please check the console and try again.</p>`;
    }
  }
});