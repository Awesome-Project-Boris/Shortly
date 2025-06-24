document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get("code");
  if (!code) return;

  // Your configuration variables
  const clientId = ""; 
  const clientSecret = ""; 
  const redirectUri = ""; 
  const tokenEndpoint = ""; 
  const APIVariable = ""; // Your API Gateway base URL

  const basicAuth = btoa(`${clientId}:${clientSecret}`);

  try {
    // --- Step 1: Exchange Cognito code for tokens (no changes here) ---
    const response = await fetch(tokenEndpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Authorization: clientSecret ? `Basic ${basicAuth}` : undefined,
      },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: clientId,
        redirect_uri: redirectUri,
        code: code,
      }),
    });

    if (!response.ok) {
      throw new Error(`Token exchange failed: ${response.statusText}`);
    }

    const tokens = await response.json();
    const idToken = tokens.id_token;
    const payload = JSON.parse(atob(idToken.split(".")[1]));
    const uuid = payload.sub;

    localStorage.setItem("userID", uuid);

    // --- Step 2: Check admin status (MODIFIED) ---
    // This now uses POST with a request body instead of a GET with a query string.
    const isAdminResp = await fetch(`${APIVariable}users/is-user-admin`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: uuid })
    });
    
    const isAdminBody = await isAdminResp.json();
    
    // The response from the new Lambda is simpler, so we can parse it directly.
    const isAdmin = isAdminResp.ok && isAdminBody.isAdmin === true;
    localStorage.setItem("isAdmin", isAdmin);

    // --- Step 3: Redirect into the application (no changes here) ---
    window.location.href = "index.html";
    
  } catch (error) {
    console.error("Callback error:", error);
    // Optionally show an error message to the user on the callback page.
    const container = document.querySelector('.spinner-container');
    if (container) {
        container.innerHTML = `<p class="loading-message text-danger">Login failed. Please try again.</p>`;
    }
  }
});
