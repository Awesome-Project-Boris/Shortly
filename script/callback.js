document.addEventListener("DOMContentLoaded", async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get("code");
  if (!code) return;

  const clientId = ""; // your Cognito App Client ID
  const clientSecret = ""; // your Cognito App Client Secret
  const redirectUri = ""; // your registered callback URI
  const tokenEndpoint = ""; // your Cognito token endpoint
  const APIVariable = ""; // your API Gateway base URL

  const basicAuth = btoa(`${clientId}:${clientSecret}`);

  try {
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

    // check admin status
    const isAdminResp = await fetch(
      `${APIVariable}Users/isadmin?userID=${uuid}`
    );
    const isAdminBody = await isAdminResp.json();
    localStorage.setItem(
      "isAdmin",
      isAdminResp.ok ? Boolean(JSON.parse(isAdminBody.body).isAdmin) : false
    );

    // redirect into Shortly
    window.location.href = "index.html";
  } catch (error) {
    console.error("Callback error:", error);
    // optionally show an error popup or message here
  }
});
