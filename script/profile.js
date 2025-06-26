$(document).ready(async function () {
  const params = new URLSearchParams(window.location.search);
  const profileID = params.get("userID");
  const me = localStorage.getItem("UserId");
  const isOwner = profileID === me;
  console.log(profileID);
  console.log(me);

  // This single API call now fetches the user's info, achievements, and links all at once.
  try {
    // NOTE: The endpoint name 'Users/profile' should match the API Gateway route for your new get_user_by_id_rewritten Lambda.
    const resp = await fetch(API + "users/get-user-by-id", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      // The request body now sends both the profile owner's ID and the logged-in user's ID.
      body: JSON.stringify({
        ProfileOwnerId: profileID,
        LoggedInUserId: me,
      }),
    });
    console.log(resp);

    if (!resp.ok) {
      throw new Error(`Failed to fetch profile data. Status: ${resp.status}`);
    }

    // The response body from the Lambda is directly parsed.
    const data = await resp.json();

    console.log("Parsed data:", data);

    const { userInfo, achievements, links } = data;

    // --- Populate Profile Header ---
    $("#userName").text(`User name: ${userInfo.Username}`);
    $("#user-name").text(`Full Name: ${userInfo.FullName}`);
    $("#country").text(`Country: ${userInfo.Country || "Not specified"}`);
    $("#user-joined").text(
      `Date Joined: ${new Date(userInfo.DateJoined).toLocaleDateString()}`
    );
    // The link count is now derived from the length of the returned links array.
    $("#user-items-count").text(`Links created: ${links.length}`);
    $(".profile-pic").attr("src", userInfo.Picture);

    // --- Render Achievements ---
    // This function will create and display the achievements section.
    renderAchievements(achievements);

    // --- Render Links DataTable ---
    // This uses the same logic as before, but now gets the 'links' data from the consolidated API call.
    initializeLinksTable(links, isOwner);
  } catch (e) {
    console.error("Failed to load profile:", e);
    // You could show an error message to the user on the page here.
    $("#userName").text("Could not load profile.");
  }

  // The friend request logic remains unchanged as it's independent of the profile data load.
  if (isOwner) {
    // If the user is viewing their own profile, show the Edit button
    $("#editProfileBtn")
      .show()
      .on("click", function () {
        // Redirect to the edit page. We assume it's named edit_profile.html
        window.location.href = `edit_profile.html`;
      });
  } else if (me) {
    // If the user is logged in but viewing someone else's profile, show the Add Friend button
    $("#friendRequestBtn")
      .show()
      .on("click", async function () {
        const $btn = $(this);
        addSpinnerToButton(this);
        try {
          const res = await fetch(API + "notif/send-friend-request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ FromUserId: me, ToUserId: profileID }),
          });
          if (!res.ok) throw new Error();
          createPopup("Friend request sent!");
          $btn.text("Request Sent").prop("disabled", true);
        } catch {
          createPopupError("Could not send friend request.");
          restoreButton(this);
        }
      });
  }

  // The modal logic for link details is also unchanged, as it depends on the DataTable,
  // which is initialized by the initializeLinksTable function.
  initializeModalLogic(isOwner);
});

/**
 * Renders the list of achievements on the profile page.
 * NOTE: This assumes you have a container in your HTML like: <div id="achievementsContainer"></div>
 * @param {Array} achievements - The array of achievement objects.
 */
function renderAchievements(achievements) {
  const container = $("#achievementsContainer");
  if (!container.length) {
    console.error(
      'Achievement container not found. Please add <div id="achievementsContainer" class="achievements-section ..."></div> to your HTML.'
    );
    return;
  }

  container.empty(); // Clear previous content

  if (!achievements || achievements.length === 0) {
    // The section title is already in the HTML, so we just add the 'empty' message.
    container.append(
      '<p class="text-muted w-100">This user has not earned any achievements yet.</p>'
    );
    return;
  }

  // Loop through each earned achievement and create a card that matches the CSS.
  achievements.forEach((ach) => {
    // Extract data with fallbacks in case the nested object doesn't exist.
    const achievementData = ach.Achievement || {};
    // MODIFIED: Construct the image path as requested
    const illustration = `${window.location.origin}/media/ach${ach.AchievementId}.png`;
    const achievementName =
      achievementData.Name || `Achievement #${ach.AchievementId}`;
    const requiredClicks = achievementData.RequiredNumber || "N/A";
    const linkName = ach.LinkName || "an unknown link";
    const earnedDate = new Date(ach.DateEarned).toLocaleDateString();

    // Construct the HTML for the achievement card to match the CSS exactly.
    const cardHtml = `
            <div class="col">
                <div class="achievement-card">
                    <img src="${illustration}" alt="${achievementName}" class="mb-3" onerror="this.src='https://placehold.co/150x150/007bff/FFFFFF?text=Award'">
                    <div class="username">${achievementName}</div>
                    <div class="link-name">For link: "${linkName}"</div>
                    <div class="clicks">Unlocked at ${requiredClicks} clicks</div>
                    <div class="date">Earned on ${earnedDate}</div>
                </div>
            </div>
        `;
    container.append(cardHtml);
  });
}

/**
 * Initializes the DataTable for the user's links.
 * @param {Array} links - The array of link objects.
 * @param {boolean} isOwner - Whether the current viewer owns the profile.
 */
function initializeLinksTable(links, isOwner) {
  const columns = [
    { data: "Name", title: "Link name" },
    { data: "Description", title: "Description" },
    // MODIFIED: Added a new column to display the full redirect URL as text
    {
      data: "LinkId",
      title: "Link",
      render: function (data, type, row) {
        // Construct the full URL and return it as plain text
        return `${window.location.origin}/main/redirect.html?code=${data}`;
      },
    },
  ];

  if (isOwner) {
    columns.push({
      data: "IsPrivate",
      title: "Visible/Private",
      render: (v) => (v ? "Private" : "Public"),
    });

    $(".section-header").first().find(".section-title").text("Your links");
    $("#linksTable").addClass("owner-view");
  }

  $("#linksTable").DataTable({
    data: links,
    columns: columns,
    paging: true,
    searching: true,
    info: false,
    lengthChange: false,
    pageLength: 10,
    destroy: true, // Important for re-initialization if needed
    language: {
      search: "_INPUT_",
      searchPlaceholder: "Filter links...",
    },
  });
}

/**
 * Sets up all the event listeners for the link details modal.
 * @param {boolean} isOwner - Whether the current viewer owns the profile.
 */
function initializeModalLogic(isOwner) {
  const linkModal = new bootstrap.Modal(
    document.getElementById("linkDetailModal")
  );
  let selectedLink = null;
  const currentUserID = localStorage.getItem("UserId");

  // Main event handler for when a link row is clicked
  $("#linksTable tbody").on("click", "tr", async function () {
    const rowData = $("#linksTable").DataTable().row(this).data();
    if (!isOwner || !rowData) return;

    selectedLink = rowData;
    $("#linkDetailModalLabel").text(`Statistics for "${selectedLink.Name}"`);

    // --- Reset modal to a loading state before showing ---
    $("#totalClicks").text("...");
    $("#createPasswordSection, #resetPasswordSection").hide();
    $("#collapsePassword").removeClass("show"); // Ensure collapsible is closed
    $("#setPasswordInput, #currentPassword, #newPassword").val("");
    $("#createPasswordError, #passwordUpdateError").text("");

    linkModal.show();

    // --- Fetch details from the backend ---
    try {
      const resp = await fetch(API + "links/get-link-details", {
        // Corrected endpoint
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ linkId: selectedLink.LinkId }),
      });
      if (!resp.ok) throw new Error("Failed to fetch link details");
      const info = await resp.json();

      // 1. Set total clicks
      $("#totalClicks").text(info.TotalClicks);

      // 2. Set visibility toggle state
      $("#linkVisibilitySwitch").prop("checked", !info.IsPrivate);
      $("#visibilityLabel")
        .text(info.IsPrivate ? "Private" : "Public")
        .css("color", info.IsPrivate ? "red" : "green");

      // 3. Set password section visibility
      if (info.IsPasswordProtected) {
        $("#resetPasswordSection").show();
      } else {
        $("#createPasswordSection").show();
      }
    } catch (e) {
      console.error("Error loading link details:", e);
      createPopupError("Could not load link details.");
      $("#totalClicks").text("N/A");
    }
  });

  // --- Event Handlers for Modal Buttons ---

  // 2. VISIBILITY TOGGLE HANDLER
  $("#linkVisibilitySwitch")
    .off("change")
    .on("change", async function () {
      const isChecked = $(this).prop("checked");
      const newIsPrivate = !isChecked;
      const visibilityLabel = $("#visibilityLabel");

      try {
        await fetch(API + "links/toggle_link_privacy", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            linkId: selectedLink.LinkId,
            isPrivate: newIsPrivate,
          }),
        });

        visibilityLabel
          .text(newIsPrivate ? "Private" : "Public")
          .css("color", newIsPrivate ? "red" : "green");
        createPopup("Visibility updated!");

        // OPTIONAL: Update the DataTable in real-time
        const table = $("#linksTable").DataTable();
        const row = table.rows(
          (idx, data, node) => data.LinkId === selectedLink.LinkId
        );
        row.data()[0].IsPrivate = newIsPrivate;
        row.invalidate().draw(false); // Update without changing page
      } catch (e) {
        // Revert toggle on failure
        $(this).prop("checked", !newIsPrivate);
        visibilityLabel
          .text(newIsPrivate ? "Public" : "Private")
          .css("color", newIsPrivate ? "green" : "red");
        createPopupError("Could not update visibility.");
      }
    });

  // 3. CREATE PASSWORD HANDLER
  $("#setPasswordBtn")
    .off("click")
    .on("click", async function () {
      const newPassword = $("#setPasswordInput").val();
      if (!newPassword || newPassword.length < 4) {
        $("#createPasswordError").text(
          "Password must be at least 4 characters."
        );
        return;
      }
      $("#createPasswordError").text("");

      try {
        // NOTE: This assumes a new endpoint for setting a password from scratch.
        // Using a PUT or a specific POST endpoint like 'set-password' is good practice.
        await fetch(API + "links/set-link-password", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            linkId: selectedLink.LinkId,
            newPassword: newPassword,
            userId: currentUserID, // Good for ownership verification
          }),
        });
        createPopup("Password has been set!");
        $("#collapsePassword").removeClass("show"); // Close collapsible
        $("#createPasswordSection").hide();
        $("#resetPasswordSection").show();
      } catch (e) {
        $("#createPasswordError").text("Could not set password.");
      }
    });

  // CHANGE PASSWORD HANDLER
  $("#changePasswordBtn")
    .off("click")
    .on("click", async function () {
      const currentPassword = $("#currentPassword").val();
      const newPassword = $("#newPassword").val();

      if (!currentPassword || !newPassword || newPassword.length < 4) {
        $("#passwordUpdateError").text(
          "Please fill both fields correctly (new password min 4 chars)."
        );
        return;
      }

      $("#passwordUpdateError").text("");
      const btn = this;
      addSpinnerToButton(btn);

      try {
        console.log("WHY?");
        console.log(
          selectedLink.LinkId +
            " " +
            currentUserID +
            " " +
            currentPassword +
            " " +
            newPassword
        );
        const resp = await fetch(API + "links/change_link_password", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            LinkId: selectedLink.LinkId,
            userId: currentUserID,
            currentPassword: currentPassword,
            newPassword: newPassword,
          }),
        });
        const result = await resp.json();
        if (!resp.ok)
          throw new Error(result.message || "An unknown error occurred.");

        createPopup("Password changed successfully!");
        $("#currentPassword, #newPassword").val("");
      } catch (e) {
        $("#passwordUpdateError").text(e.message);
      } finally {
        restoreButton(btn);
      }
    });

  $("#removePasswordBtn")
    .off("click")
    .on("click", async function () {
      const isConfirmed = await Swal.fire({
        title: "Are you sure?",
        text: "This will permanently remove the password from this link.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        confirmButtonText: "Yes, remove it!",
      }).then((result) => result.isConfirmed);

      if (!isConfirmed) return;

      try {
        const resp = await fetch(API + "links/remove-link-password", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            linkId: selectedLink.LinkId,
            userId: currentUserID,
          }),
        });

        if (!resp.ok) {
          const errorData = await resp.json();
          throw new Error(errorData.message || "Failed to remove password.");
        }

        createPopup("Password removed successfully!");
        $("#resetPasswordSection").hide();
        $("#createPasswordSection").show();
      } catch (e) {
        console.error("Remove password failed:", e);
        createPopupError(e.message || "Could not remove password.");
      }
    });

  // DELETE LINK HANDLER
  $("#deleteLinkBtn")
    .off("click")
    .on("click", async function () {
      const isConfirmed = await Swal.fire({
        title: "Are you sure?",
        text: "You won't be able to revert this!",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        confirmButtonText: "Yes, delete it!",
      }).then((result) => result.isConfirmed);

      if (!isConfirmed) return;

      try {
        await fetch(API + "links", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ LinkId: selectedLink.LinkId }),
        });
        createPopup("Link deleted");
        linkModal.hide();
        $("#linksTable")
          .DataTable()
          .row((idx, data, node) => data.LinkId === selectedLink.LinkId)
          .remove()
          .draw();
      } catch (e) {
        createPopupError("Could not delete link.");
      }
    });
}

function renderCountryStats(statsData) {
  const container = $("#countryStatsContainer");
  container.empty();

  if (!statsData || Object.keys(statsData).length === 0) {
    container.html(
      '<p class="text-muted small m-0">No country-specific data available.</p>'
    );
    return;
  }

  const maxClicks = Math.max(...Object.values(statsData));
  const sortedCountries = Object.entries(statsData).sort((a, b) => b[1] - a[1]);

  sortedCountries.forEach(([country, clicks]) => {
    const barWidth = (clicks / maxClicks) * 100;
    const barHtml = `
                <div class="stat-bar" style="width: ${barWidth}%;">
                    <span>${country}</span>
                    <span>${clicks}</span>
                </div>
            `;
    container.append(barHtml);
  });
}

async function handleProtectedLinkClick(linkData) {
  const passwordModal = new bootstrap.Modal(
    document.getElementById("passwordAccessModal")
  );
  const passwordInput = $("#accessPasswordInput");
  const errorMsg = $("#passwordAccessError");
  const unlockBtn = $("#unlockLinkBtn");

  passwordInput.val("").removeClass("is-invalid");
  errorMsg.text("");
  passwordModal.show();

  unlockBtn.off("click").on("click", async function () {
    const password = passwordInput.val();
    if (!password) {
      errorMsg.text("Password cannot be empty.");
      passwordInput.addClass("is-invalid");
      return;
    }

    addSpinnerToButton(this);
    errorMsg.text("");
    passwordInput.removeClass("is-invalid");

    try {
      const resp = await fetch(API + "links/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          linkId: linkData.LinkId,
          password: password,
        }),
      });
      const result = await resp.json();

      if (result.accessGranted) {
        passwordModal.hide();
        window.location.href = result.originalUrl;
      } else {
        errorMsg.text(result.message || "Incorrect password.");
        passwordInput.addClass("is-invalid");
      }
    } catch (e) {
      console.error("Password verification failed:", e);
      errorMsg.text("An error occurred. Please try again.");
    } finally {
      restoreButton(btn);
    }
  });
}
