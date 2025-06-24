// In Shortly/script/global.js

// --- Global Configuration ---
const API = "https://rhdxlt92ul.execute-api.us-east-1.amazonaws.com/prod/"; // e.g. "https://xyz.execute-api.us-east-1.amazonaws.com/prod/"
const websiteURL = ""; // e.g. "https://yourbucket.s3.amazonaws.com"
const cognitoDomain = ""; // e.g. "https://your-auth-domain.auth.us-east-1.amazoncognito.com"
const clientId = ""; // your Cognito App Client ID
const redirectUri = ""; // the exact redirect URI registered in Cognito

const currentUserID = localStorage.getItem("UserId");
const isAdmin = localStorage.getItem("isAdmin") === "true";

// --- Page Load Event ---
document.addEventListener("DOMContentLoaded", () => {
  buildNavBar();
  // This function handles checks for logged-in users
  runUserChecks();
});


// --- UI Building ---

function buildNavBar() {
  const header = document.querySelector("header.navbar");
  if (!header) return;

  // NAVBAR HTML structure with the friend icon
  header.innerHTML = `
    <div class="container d-flex align-items-center">
      <div id="nav-friends-container" class="notification-container">
        <button id="nav-friends-toggle" class="btn btn-outline-primary me-3 btn-lg" type="button" title="Friends & Requests">
            <img src="../media/friend.png" width="24" alt="Social" style="vertical-align: middle;">
        </button>
      </div>
      <button id="nav-home" class="btn btn-primary btn-lg me-3">Home</button>
      <input id="nav-search" class="form-control search-input me-auto" placeholder="Search…"/>
      <div id="nav-buttons" class="d-flex ms-3"></div>
    </div>`;

  // Attach event handlers
  header.querySelector("#nav-home").onclick = () => window.location.href = "index.html";

  header.querySelector("#nav-search").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const q = e.target.value.trim().toLowerCase();
      localStorage.setItem("searchQuery", q);
      window.location.href = "index.html";
    }
  });

  // Click handler for the Friends/Social button
  header.querySelector("#nav-friends-toggle").onclick = () => {
    const container = document.getElementById("nav-friends-container");
    const dot = container.querySelector('.notification-dot');
    if (dot) dot.remove();

    if (currentUserID) {
      fetch(API + 'notif/check-unread-notifications', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: currentUserID })
      }).catch(error => console.error('Error sending mark as read request:', error));
    }

    const offcanvasEl = document.getElementById("friendsOffcanvas");
    const off = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    off.toggle();
  };

  // Build login/logout/profile buttons
  const btns = header.querySelector("#nav-buttons");
  btns.innerHTML = "";
  if (!currentUserID) {
    btns.insertAdjacentHTML("beforeend", `<button id="nav-login" class="btn btn-primary">Login</button>`);
    header.querySelector("#nav-login").onclick = () => {
      window.location.href = `https://us-east-1zsxqwhoz7.auth.us-east-1.amazoncognito.com/login?client_id=4o8p2umpmd1i3rikvv9jct2led&response_type=code&scope=email+openid+phone&redirect_uri=https%3A%2F%2Fshortly-rlt.s3.us-east-1.amazonaws.com%2Fmain%2Fcallback.html`;
    };
  } else {
    if (isAdmin) {
      btns.insertAdjacentHTML("beforeend", `<button id="nav-dashboard" class="btn btn-primary me-2">Dashboard</button>`);
      header.querySelector("#nav-dashboard").onclick = () => window.location.href = "admin.html";
    } else {
      btns.insertAdjacentHTML("beforeend", `<button id="nav-profile" class="btn btn-primary me-2">Profile</button>`);
      header.querySelector("#nav-profile").onclick = () => window.location.href = `profile.html?userID=${currentUserID}`;
    }
    btns.insertAdjacentHTML("beforeend", `<button id="nav-logout" class="btn btn-secondary">Logout</button>`);
    header.querySelector("#nav-logout").onclick = signOff;
  }

  // Ensure the offcanvas HTML is in the DOM
  if (!document.getElementById("friendsOffcanvas")) {
    document.body.insertAdjacentHTML("beforeend", `
      <div class="offcanvas offcanvas-start" tabindex="-1" id="friendsOffcanvas" aria-labelledby="friendsOffcanvasLabel">
        <div class="offcanvas-header">
          <h5 id="friendsOffcanvasLabel">Notifications</h5>
          <button type="button" class="btn-close text-reset" data-bs-dismiss="offcanvas" aria-label="Close"></button>
        </div>
        <div class="offcanvas-body">
          <h6>Friend Requests</h6>
          <div id="friendRequestsContainer"></div>
          <hr class="my-3">
          <h6>Recent Activity</h6>
          <div id="generalNotificationsContainer"></div>
          <hr class="my-3">
          <h6>Friends List</h6>
          <div id="friendsListContainer"></div>
        </div>
      </div>`);
  }

  // Attach the master function to the offcanvas show event
  const offcanvasEl = document.getElementById("friendsOffcanvas");
  offcanvasEl.addEventListener("show.bs.offcanvas", loadOffcanvasContent);
}


// --- User & Session Management ---

function signOff() {
  localStorage.removeItem("UserId");
  localStorage.removeItem("isAdmin");
  window.location.href = "index.html";
}

function goToProfile() {
  if (currentUserID) {
    // Navigating to profile still uses a query string, as it's part of the page URL itself.
    window.location.href = `profile.html?userID=${currentUserID}`;
  } else {
    // Fallback to login if not logged in
    const loginBtn = document.getElementById("nav-login");
    if (loginBtn) loginBtn.click();
  }
}

// --- Off-Canvas Notification Logic ---

async function loadOffcanvasContent() {
  if (!currentUserID) return;

  const requestsContainer = document.getElementById("friendRequestsContainer");
  const generalContainer = document.getElementById("generalNotificationsContainer");

  // Show loading spinners
  requestsContainer.innerHTML = `<div class="spinner-border spinner-border-sm text-primary mx-auto d-block" role="status"></div>`;
  generalContainer.innerHTML = `<div class="spinner-border spinner-border-sm text-primary mx-auto d-block" role="status"></div>`;

  // Fetch notifications and friends in parallel for speed
  try {
    const [notificationsResp] = await Promise.all([
      // MODIFIED: Using POST with a body instead of GET with a query string.
      fetch(API + 'notif', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: currentUserID })
      }),
      loadFriendsList() // This function handles its own container
    ]);

    if (!notificationsResp.ok) throw new Error("Failed to fetch notifications");

    const data = await notificationsResp.json();

    renderFriendRequests(data.friendRequests || []);
    renderOtherNotifications(data.otherNotifications || []);

  } catch (e) {
    console.error("Could not load offcanvas content:", e);
    requestsContainer.innerHTML = `<div class="text-muted small">Could not load requests.</div>`;
    generalContainer.innerHTML = `<div class="text-muted small">Could not load notifications.</div>`;
  }
}

function renderFriendRequests(requests) {
  const container = document.getElementById("friendRequestsContainer");
  if (!requests || requests.length === 0) {
    container.innerHTML = '<div class="text-muted small p-2">No pending friend requests.</div>';
    return;
  }

  container.innerHTML = ""; // Clear spinner
  requests.forEach(req => {
    const fromUser = req.FromUser || {};
    const username = fromUser.Username || 'A user';
    const picture = fromUser.Picture || 'https://placehold.co/40x40/007bff/FFFFFF?text=??';

    const card = document.createElement("div");
    card.className = "friend-request-card";
    card.innerHTML = `
            <img src="${picture}" alt="${username}" class="rounded-circle" width="40" height="40" />
            <div class="friend-request-info flex-grow-1 mx-2">
                <strong>${username}</strong> sent you a friend request.
            </div>
            <div class="friend-request-actions">
                <button class="btn btn-success btn-sm" title="Accept">✓</button>
                <button class="btn btn-danger btn-sm" title="Reject">✕</button>
            </div>`;

    card.querySelector(".btn-success").onclick = () => respondToRequest(req.NotifId, true, card);
    card.querySelector(".btn-danger").onclick = () => respondToRequest(req.NotifId, false, card);
    container.appendChild(card);
  });
}

function renderOtherNotifications(notifications) {
  const container = document.getElementById("generalNotificationsContainer");
  if (!notifications || notifications.length === 0) {
    container.innerHTML = '<div class="text-muted small p-2">No new notifications.</div>';
    return;
  }

  container.innerHTML = ""; // Clear spinner
  notifications.forEach(note => {
    const card = document.createElement("div");
    card.className = "notification-card";
    card.innerHTML = `<p class="notification-text mb-0">${note.Text}</p>`;
    card.onclick = () => window.location.href = `profile.html?userID=${currentUserID}`;
    container.appendChild(card);
  });
}

async function respondToRequest(notificationID, accept, cardEl) {
  try {
    // This fetch call is already using POST with a body, so it's correct.
    const resp = await fetch(`${API}users/respond-friend-request`, {
      // method: "POST",
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notificationID, accept }),
    });
    if (!resp.ok) throw new Error("Response not OK");

    cardEl.style.transition = 'opacity 0.5s ease';
    cardEl.style.opacity = '0';
    setTimeout(() => cardEl.remove(), 500);

  } catch (e) {
    console.error("Respond failed:", e);
    createPopupError("Could not update request");
  }
}

async function loadFriendsList() {
  const container = document.getElementById("friendsListContainer");
  container.innerHTML = `<div class="spinner-border spinner-border-sm text-primary mx-auto d-block" role="status"></div>`;

  try {
    // MODIFIED: Using POST with a body instead of GET with a query string.
    const resp = await fetch(API + "users/get-user-friends", {
      //method: 'POST',
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId: currentUserID })
    });
    if (!resp.ok) throw new Error("Failed to fetch friends list");
    const data = await resp.json();
    const friends = typeof data.body === "string" ? JSON.parse(data.body) : data.body;

    if (!friends || friends.length === 0) {
      container.innerHTML = '<div class="text-muted small p-2">You have no friends yet.</div>';
      return;
    }

    container.innerHTML = "";
    friends.forEach(u => {
      const card = document.createElement("div");
      card.className = "friend-card"; // This is a clickable card
      card.innerHTML = `
                <img src="${u.picture || 'https://placehold.co/40x40/6c757d/FFFFFF?text=??'}" alt="${u.username}" class="rounded-circle" width="40" height="40"/>
                <div class="friend-info ms-2">${u.username}</div>`;
      card.onclick = () => window.location.href = `profile.html?userID=${u.userID}`;
      container.appendChild(card);
    });
  } catch (e) {
    console.error("Failed to load friends list:", e);
    container.innerHTML = `<div class="text-muted small">Could not load friends.</div>`;
  }
}


// --- User Status Checks (Runs on Page Load) ---

async function runUserChecks() {
  if (!currentUserID) return;

  // Check for Unread Notifications
  try {
    // MODIFIED: Using POST with a body instead of GET with a query string.
    const resp = await fetch(API + 'notif/check_unread_notifications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ UserId: currentUserID })
    });
    const data = await resp.json();
    if (data.hasUnreadNotifications) {
      const container = document.getElementById('nav-friends-container');
      if (container && !container.querySelector('.notification-dot')) {
        container.insertAdjacentHTML('beforeend', '<div class="notification-dot"></div>');
      }
    }
  } catch (e) {
    console.error("Failed to check for notifications:", e);
  }

  // Check if Account is Active
  try {
    // MODIFIED: Using POST with a body instead of GET with a query string.
    const r = await fetch(API + 'users/is-user-banned', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ userId: currentUserID })
    });
    const data = await r.json();
    const user = typeof data.body === 'string' ? JSON.parse(data.body) : data.body;
    if (!user.isActive) {
      Swal.fire({
        title: "Account Deactivated",
        text: "Your account is currently inactive. Please contact an administrator.",
        icon: "warning",
        allowOutsideClick: false,
        confirmButtonText: 'Logout'
      }).then(() => signOff());
    }
  } catch (e) {
    console.error("Failed to check user active status:", e);
  }
}


// --- Utility Functions ---

function createPopup(message) {
  Swal.fire({
    position: "top",
    title: `<div class="text-center h5">${message}</div>`,
    icon: "success",
    toast: true,
    showConfirmButton: false,
    timer: 1500,
  });
}
function createPopupError(message) {
  Swal.fire({
    position: "top",
    title: message,
    icon: "error",
    toast: true,
    showConfirmButton: false,
    timer: 2500,
  });
}
function createPopupWarning(message) {
  Swal.fire({
    position: "top",
    title: `<div class="text-center h5">${message}</div>`,
    icon: "warning",
    toast: true,
    showConfirmButton: false,
    timer: 2500, // A bit longer for warnings
  });
}
function addSpinnerToButton(button) {
  if (!button || !(button instanceof HTMLButtonElement)) return;
  button.setAttribute("data-original-content", button.innerHTML);
  button.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;
  button.disabled = true;
}
function restoreButton(button) {
  if (!button || !(button instanceof HTMLButtonElement)) return;
  const orig = button.getAttribute("data-original-content");
  if (orig) {
    button.innerHTML = orig;
    button.removeAttribute("data-original-content");
  }
  button.disabled = false;
}
