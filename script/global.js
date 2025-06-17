const API = ""; // e.g. "https://xyz.execute-api.us-east-1.amazonaws.com/prod/"
const websiteURL = ""; // e.g. "https://yourbucket.s3.amazonaws.com"
const cognitoDomain = ""; // e.g. "https://your-auth-domain.auth.us-east-1.amazoncognito.com"
const clientId = ""; // your Cognito App Client ID
const redirectUri = ""; // the exact redirect URI registered in Cognito


const currentUserID = localStorage.getItem("userID");
const isAdmin = localStorage.getItem("isAdmin") === "true";


// TEMP DISABLE!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

// if (
//   !currentUserID &&
//   !window.location.pathname.endsWith("index.html") &&
//   !(
//     window.location.pathname.endsWith("profile.html") &&
//     window.location.search.includes("userID=")
//   )
// ) {
//   window.location.href = "index.html";
// }

document.addEventListener("DOMContentLoaded", () => {
  buildNavBar();
  checkAccountActive();
});

function buildNavBar() {
  const header = document.querySelector("header.navbar");
  if (!header) return;

  // NAVBAR HTML structure
  header.innerHTML = `
    <div class="container d-flex align-items-center">
      <div id="nav-friends-container" class="notification-container">
        <button
          id="nav-friends-toggle"
          class="btn btn-outline-primary me-3 btn-lg"
          type="button"
          title="Friends & Requests"
        >👥</button>
      </div>
      <button id="nav-home" class="btn btn-primary btn-lg me-3">
        Home
      </button>
      <input
        id="nav-search"
        class="form-control search-input me-auto"
        placeholder="Search…"
      />
      <div id="nav-buttons" class="d-flex ms-3"></div>
    </div>
  `;

  // --- Click handler for the Friends/Social button ---
  header.querySelector("#nav-friends-toggle").onclick = () => {
    // 1. Give instant visual feedback by removing the dot.
    const container = document.getElementById("nav-friends-container");
    const dot = container.querySelector('.notification-dot');
    if (dot) {
      dot.remove();
    }
    
    // 2. Call the new Lambda in the background to mark notifications as read.
    if (currentUserID) {
      fetch(API + 'notifications/markread', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: currentUserID })
      })
      .then(response => {
        if (!response.ok) {
          console.error('API call to mark notifications as read failed.');
        } else {
          console.log('Successfully marked notifications as read.');
        }
      })
      .catch(error => {
        console.error('Error sending mark as read request:', error);
      });
    }

    // 3. Show the offcanvas panel immediately without waiting for the API.
    const offcanvasEl = document.getElementById("friendsOffcanvas");
    const off = bootstrap.Offcanvas.getOrCreateInstance(offcanvasEl);
    off.toggle();
  };

  // (The rest of the buildNavBar function for home, search, login, etc. remains the same...)
  header.querySelector("#nav-home").onclick = () => {
    window.location.href = "index.html";
  };
  
  header.querySelector("#nav-search").addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const q = e.target.value.trim().toLowerCase();
      localStorage.setItem("searchQuery", q);
      window.location.href = "index.html";
    }
  });
  
   const btns = header.querySelector("#nav-buttons");
  btns.innerHTML = "";

  if (!currentUserID) {
    btns.insertAdjacentHTML(
      "beforeend",
      `<button id="nav-login" class="btn btn-primary">Login</button>`
    );
    header.querySelector("#nav-login").onclick = () => {
      window.location.href =
        `${cognitoDomain}/login?client_id=${clientId}` +
        `&response_type=code&scope=email+openid+phone&redirect_uri=${redirectUri}`;
    };
  } else {
    if (isAdmin) {
      btns.insertAdjacentHTML(
        "beforeend",
        `<button id="nav-dashboard" class="btn btn-primary me-2">Dashboard</button>`
      );
      header.querySelector("#nav-dashboard").onclick = () => {
        window.location.href = "admin.html";
      };
    } else {
      btns.insertAdjacentHTML(
        "beforeend",
        `<button id="nav-profile" class="btn btn-primary me-2">Profile</button>`
      );
      header.querySelector("#nav-profile").onclick = () => {
        window.location.href = `profile.html?userID=${currentUserID}`;
      };
    }

    btns.insertAdjacentHTML(
      "beforeend",
      `<button id="nav-logout" class="btn btn-secondary">Logout</button>`
    );
    header.querySelector("#nav-logout").onclick = signOff;
  }
  
    if (!document.getElementById("friendsOffcanvas")) {
    document.body.insertAdjacentHTML(
      "beforeend",
      `
      <div class="offcanvas offcanvas-start" tabindex="-1"
           id="friendsOffcanvas" aria-labelledby="friendsOffcanvasLabel">
        <div class="offcanvas-header">
          <h5 id="friendsOffcanvasLabel">Friends & Requests</h5>
          <button type="button" class="btn-close text-reset"
                  data-bs-dismiss="offcanvas" aria-label="Close"></button>
        </div>
        <div class="offcanvas-body">
          <h6>Notifications</h6>
          <div id="friendRequestsContainer"></div>
          <h6 class="mt-3">Friends</h6>
          <div id="friendsListContainer"></div>
        </div>
      </div>
    `
    );
  }

  const offcanvasEl = document.getElementById("friendsOffcanvas");
  offcanvasEl.addEventListener("show.bs.offcanvas", () => {
    loadFriendRequests();
    loadFriendsList();
  });
}

function signOff() {
  localStorage.removeItem("userID");
  localStorage.removeItem("isAdmin");
  window.location.href = "index.html";
}


function goToProfile() {
  if (currentUserID) {
    window.location.href = `profile.html?userID=${currentUserID}`;
  } else {
    // fallback to login
    window.location.href =
      `${cognitoDomain}/login?client_id=${clientId}` +
      `&response_type=code&scope=email+openid+phone&redirect_uri=${redirectUri}`;
  }
}

function generateUUID() {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0,
      v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

async function sendEmail(recipientEmail, subject, mailBody) {
  try {
    const response = await fetch(API + `Users/mail`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recipient_email: recipientEmail,
        subject: subject,
        mail_body: mailBody,
      }),
    });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`Error: ${errorData.message || "Failed to send email."}`);
    }
    await response.json();
  } catch (e) {
    console.error("sendEmail failed:", e);
  }
}


function createPopup(message) {
  Swal.fire({
    position: "top",
    title: `<div class="text-center h5">${message}</div>`,
    icon: "success",
    toast: true,
    showClass: { popup: "animate__animated animate__zoomIn animate__faster" },
    hideClass: { popup: "animate__animated animate__zoomOut animate__faster" },
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
    showClass: { popup: "animate__animated animate__zoomIn animate__faster" },
    hideClass: { popup: "animate__animated animate__zoomOut animate__faster" },
    showConfirmButton: false,
    timer: 2500,
  });
}
function createPopupWarning(message) {
  Swal.fire({
    position: "top",
    title: message,
    icon: "warning",
    toast: true,
    showClass: { popup: "animate__animated animate__zoomIn animate__faster" },
    hideClass: { popup: "animate__animated animate__zoomOut animate__faster" },
    showConfirmButton: false,
    timer: 2500,
  });
}

function addSpinnerToButton(button) {
  if (!button || !(button instanceof HTMLButtonElement)) return;
  button.setAttribute("data-original-content", button.innerHTML);
  button.innerHTML += `<span class="spinner-border spinner-border-sm ms-2" role="status" aria-hidden="true"></span>`;
  button.disabled = true;
  button.classList.add("btn-disabled");
}
function restoreButton(button) {
  if (!button || !(button instanceof HTMLButtonElement)) return;
  const orig = button.getAttribute("data-original-content");
  if (orig) {
    button.innerHTML = orig;
    button.removeAttribute("data-original-content");
  }
  button.disabled = false;
  button.classList.remove("btn-disabled");
}


function checkAccountActive() {
  if (!currentUserID) return;
  fetch(API + `Users/byid?userID=${currentUserID}`)
    .then((r) => r.json())
    .then((data) => {
      const user =
        typeof data.body === "string" ? JSON.parse(data.body) : data.body;
      if (!user.isActive) {
        Swal.fire({
          title: "User Deactivated",
          text: "Please contact the administrator.",
          icon: "warning",
          showConfirmButton: false,
          timer: 2500,
        });
      }
    })
    .catch(() => {});
}

///////////////////////////////////////////////////////////////////////////////////////////////////////// offcanvas


async function loadFriendRequests() {
  const me = localStorage.getItem("userID");
  const container = document.getElementById("friendRequestsContainer");
  container.innerHTML =
    "" +
    '<div class="loading-spinner text-center">' +
    '  <div class="spinner-border spinner-border-sm" role="status"></div>' +
    "</div>";

  let requests;
  if (
    window.MOCK_FRIEND_REQUESTS &&
    Array.isArray(window.MOCK_FRIEND_REQUESTS)
  ) {
    requests = window.MOCK_FRIEND_REQUESTS;
  } else {
    const resp = await fetch(API + "Friends/requests?userID=" + me);
    const data = await resp.json();
    // data.body may be JSON string or object
    requests =
      typeof data.body === "string" ? JSON.parse(data.body) : data.body;
  }

  // empty / none
  if (!requests || requests.length === 0) {
    container.innerHTML = '<div class="text-muted">No pending requests</div>';
    return;
  }

  // render each
  container.innerHTML = "";
  requests.forEach(function (req) {
    const card = document.createElement("div");
    card.className = "friend-request-card";
    card.innerHTML =
      "" +
      '<img src="' +
      req.picture +
      '" alt="' +
      req.username +
      '" />' +
      '<div class="friend-request-info">' +
      req.username +
      "</div>" +
      '<div class="friend-request-actions">' +
      '  <button class="btn btn-success btn-sm">✓</button>' +
      '  <button class="btn btn-danger btn-sm">✕</button>' +
      "</div>";

    card.querySelector(".btn-success").onclick = function () {
      respondToRequest(req.notificationID, true, card);
    };
    card.querySelector(".btn-danger").onclick = function () {
      respondToRequest(req.notificationID, false, card);
    };
    container.appendChild(card);
  });
}

async function loadFriendsList() {
  const me = localStorage.getItem("userID");
  const container = document.getElementById("friendsListContainer");
  container.innerHTML =
    "" +
    '<div class="loading-spinner text-center">' +
    '  <div class="spinner-border spinner-border-sm" role="status"></div>' +
    "</div>";

  // decide source
  let friends;
  if (window.MOCK_FRIENDS && Array.isArray(window.MOCK_FRIENDS)) {
    friends = window.MOCK_FRIENDS;
  } else {
    const resp = await fetch(API + "Friends/list?userID=" + me);
    const data = await resp.json();
    friends = typeof data.body === "string" ? JSON.parse(data.body) : data.body;
  }

  // empty / none
  if (!friends || friends.length === 0) {
    container.innerHTML = '<div class="text-muted">You have no friends</div>';
    return;
  }

  container.innerHTML = "";
  friends.forEach(function (u) {
    const card = document.createElement("div");
    card.className = "friend-card";
    card.innerHTML =
      "" +
      '<img src="' +
      u.picture +
      '" alt="' +
      u.username +
      '" />' +
      '<div class="friend-info">' +
      u.username +
      "</div>";
    card.onclick = function () {
      window.location.href = "profile.html?userID=" + u.userID;
    };
    container.appendChild(card);
  });
}

async function respondToRequest(notificationID, accept, cardEl) {
  try {
    const resp = await fetch(`${API}Friends/respond`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ notificationID, accept }),
    });
    if (!resp.ok) throw new Error();
    // replace buttons with text
    cardEl.querySelector(".friend-request-actions").innerHTML = accept
      ? "Accepted"
      : "Rejected";
  } catch (e) {
    console.error("Respond failed:", e);
    createPopupError("Could not update request");
  }
}
