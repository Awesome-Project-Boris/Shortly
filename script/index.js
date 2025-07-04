// index.js
$(document).ready(async function () {
  const userID = localStorage.getItem("UserId");
  const API_URL = API; // Assuming 'API' is defined in global.js
  const site = `https://shortly-rlt.s3.us-east-1.amazonaws.com`;

  // MODIFIED: Read the search query from the URL querystring instead of localStorage
  const urlParams = new URLSearchParams(window.location.search);
  const globalSearchQuery = urlParams.get('q') || "";

  // Helper function to copy text to clipboard
  function copyToClipboard(text) {
    const el = document.createElement("textarea");
    el.value = text;
    el.setAttribute("readonly", "");
    el.style.position = "absolute";
    el.style.left = "-9999px";
    document.body.appendChild(el);
    el.select();
    document.execCommand("copy");
    document.body.removeChild(el);
  }

  // Define event handlers for the action buttons in the table
  window.actionEvents = {
    "click .action-copy": function (e, value, row, index) {
      e.stopPropagation(); // Prevent the row's click event from firing
      const link = `${site}/main/redirect.html?code=${row.LinkId}`;
      copyToClipboard(link);
      createPopup("Link copied!"); // This function is from global.js
    },
    "click .action-open": function (e, value, row, index) {
      e.stopPropagation(); // Prevent the row's click event from firing
      const link = `${site}/main/redirect.html?code=${row.LinkId}`;
      window.open(link, "_blank"); // Open link in a new tab
    },
  };

  $("#linksTable").bootstrapTable({
    url: `${API_URL}links/get-public-links`, // The URL to your new Lambda
    method: "get", // Use GET as this endpoint doesn't require a body
    classes: "table-striped table-hover",
    pagination: true,
    pageSize: 20,
    search: true,
    searchText: globalSearchQuery, // MODIFIED: Use the query from the URL
    searchOnEnterKey: false,
    searchTimeOut: 300,
    escape: false,
    // This handler ensures the data from the Lambda is read correctly
    responseHandler: function (res) {
      // The Lambda now returns the array directly in the body
      return res;
    },
    columns: [
      {
        field: "Name",
        title: "Link name",
      },
      {
        field: "Description",
        title: "Description",
      },
      {
        field: "LinkId",
        title: "Link",
        formatter: (value, row) => {
          const url = `${site}/main/redirect.html?code=${row.LinkId}`;
          const displayText =
            site.replace("https://", "") + "/.../" + row.LinkId;
          return `<a href="${url}" target="_blank" title="${url}">${displayText}</a>`;
        },
      },
      {
        field: "actions",
        title: "Actions",
        align: "center",
        width: 160, // UPDATED: Increased width for larger buttons
        events: window.actionEvents, // wire up the events
        formatter: () => {
          // This HTML will be inserted into the cell
          return `
            <div class="table-action-buttons">
              <button class="btn btn-outline-secondary btn-sm me-2 action-copy" title="Copy link">Copy</button>
              <button class="btn btn-outline-primary btn-sm action-open" title="Open link in new tab">Open</button>
            </div>
          `;
        },
      },
      {
        field: "IsPasswordProtected",
        title: '<img src="../media/lock.png" width="16" alt="Protected">',
        align: "center",
        width: 40,
        formatter: (value) =>
          value
            ? '<img src="../media/lock.png" width="16" alt="Protected">'
            : "",
      },
    ],
    onClickRow: function (row) {
      const userID = localStorage.getItem("UserId");

      // Prevent action on the link itself, allow redirection only from the link text
      if (event.target.tagName === "A") {
        return;
      }

      // Prevent action on the link itself, allow redirection only from the link text
      if (event.target.tagName === "A" || event.target.closest("button")) {
        return;
      }

      if (String(row.ownerId) === userID) {
        // If the user owns the link, you might want to redirect them to the edit page or do nothing.
        // For now, we'll just log it and prevent further action.
        console.log("Owner clicked their own link row.");
        return;
      }
    },
  });

  // Go→Link button
  $("#goToLinkBtn").click(function () {
    const pw = $("#accessPassword").val().trim();
    if (window._needsPassword && !pw) {
      return $("#accessError").text("Password required");
    }
    $("#linkAccessModal").modal("hide");
    window.location.href = window._needsPassword
      ? `${window._currentShortUrl}?pw=${encodeURIComponent(pw)}`
      : window._currentShortUrl;
  });

  // action buttons
  $("#newLinkBtn").click(() => {
    if (!userID) return createPopupWarning("Please log in to add a link");
    window.location.href = "new_item.html";
  });

  $("#friendsBtn").click(() => {
    window.location.href = "social.html";
  });

  // --- Create Link Modal Specific Logic ---

  // Show/hide password input based on toggle
  $("#isPasswordProtected").on("change", function () {
    if ($(this).is(":checked")) {
      $("#passwordInputContainer").slideDown();
    } else {
      $("#passwordInputContainer").slideUp();
      $("#linkPassword").val("").removeClass("is-invalid"); // Clear password on hide
    }
  });

  // Character counters for name and description
  $("#linkName, #linkDescription").on("input", function () {
    const el = $(this);
    const maxLength = el.attr("maxlength");
    const currentLength = el.val().length;
    el.next("small").text(`${currentLength}/${maxLength}`);
  });

  // Handle the final "Create Link" button click
  $("#submitCreateLinkBtn").click(async function () {
    const userID = localStorage.getItem("UserId");
    if (!userID) return createPopupError("You must be logged in.");

    const form = $("#createLinkForm")[0];
    const originalUrlInput = $("#originalUrl");
    const passwordInput = $("#linkPassword");
    const isPasswordProtected = $("#isPasswordProtected").is(":checked");

    // --- Client-side Validation ---
    let isValid = true;
    // Reset previous errors
    $(".is-invalid").removeClass("is-invalid");

    // Check URL validity
    if (!form.checkValidity() || !originalUrlInput.val().trim()) {
      originalUrlInput.addClass("is-invalid");
      isValid = false;
    }

    // Check password if protection is enabled
    if (isPasswordProtected && !passwordInput.val().trim()) {
      passwordInput.addClass("is-invalid");
      isValid = false;
    }

    if (!isValid) return;

    // --- Prepare and Send API Request ---
    const btn = this;
    addSpinnerToButton(btn);

    const payload = {
      url: originalUrlInput.val().trim(),
      userId: userID,
      name: $("#linkName").val().trim(),
      description: $("#linkDescription").val().trim(),
      isPrivate: $("#isPrivate").is(":checked"),
      isPasswordProtected: isPasswordProtected,
      password: passwordInput.val(), // Send even if empty, Lambda will handle it
    };

    try {
      const resp = await fetch(API + "links", {
        // Assuming your endpoint is '/links'
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const errorData = await resp.json();
        throw new Error(errorData.error || "Failed to create link.");
      }

      const result = await resp.json();

      // Hide the modal on success
      bootstrap.Modal.getInstance($("#createLinkModal")[0]).hide();

      // Show a success message with the new short URL
      Swal.fire({
        icon: "success",
        title: "Link Created!",
        html: `Your new short link is: <br><a href="${site + result.LinkId
          }" target="_blank">${site + result.LinkId}</a>`,
      });

      // Optionally, refresh the main links table to show the new link
      $("#linksTable").bootstrapTable("refresh");
    } catch (e) {
      console.error("Create link failed:", e);
      createPopupError(e.message);
    } finally {
      restoreButton(btn);
    }
  });

  $("#friendsBtn").click(() => {
    window.location.href = "social.html";
  });

  // modals
  const createModal = new bootstrap.Modal($("#createGroupModal")[0]);
  const shareModal = new bootstrap.Modal($("#shareLinkModal")[0]);

  // CREATE GROUP
  let groupEmails = [],
    groupFriendIDs = [];
  $("#createGroupBtn").click(function () {
    if (!userID)
      return createPopupWarning("Please log in to create mailing groups!");
    groupEmails = [];
    groupFriendIDs = [];
    $("#groupName").val("").removeClass("is-invalid");
    $("#groupNameError,#groupEmailError,#groupFriendsError").text("");
    $("#groupNameCounter").text("0/50");
    $("#groupEmailInput").val("");
    renderGroupEmailList();
    renderGroupFriendsList();
    createModal.show();
  });

  $("#groupName").on("input", function () {
    const len = this.value.length;
    $("#groupNameCounter").text(`${len}/50`);
    $(this).toggleClass("is-invalid", !len || len > 50);
  });
  $("#addGroupEmailBtn").click(() => {
    const val = $("#groupEmailInput").val().trim().toLowerCase();
    $("#groupEmailError").text("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val))
      return $("#groupEmailError").text("Enter a valid email");
    if (groupEmails.includes(val))
      return $("#groupEmailError").text("Already added");
    groupEmails.push(val);
    $("#groupEmailInput").val("");
    renderGroupEmailList();
  });
  function renderGroupEmailList() {
    const $c = $("#groupEmailList").empty();
    groupEmails.forEach((e) => {
      const $chip = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${e}
          <button type="button" class="btn-close btn-close-white btn-sm ms-2"></button>
        </span>`);
      $chip.find("button").click(() => {
        groupEmails = groupEmails.filter((x) => x !== e);
        renderGroupEmailList();
      });
      $c.append($chip);
    });
  }
  function renderGroupFriendsList(friends) {
    const $c = $("#groupFriendsList").empty();
    if (friends != null) {
      friends.forEach((f) => {
        const $lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox" class="form-check-input me-1" value="${f.userID}">
          <img src="${f.picture}" width="24" height="24" class="rounded-circle">
          <span class="ms-1">${f.username}</span>
        </label>`);
        $lbl.find("input").on("change", function () {
          const id = this.value;
          if (this.checked) groupFriendIDs.push(id);
          else groupFriendIDs = groupFriendIDs.filter((x) => x !== id);
        });
        $c.append($lbl);
      });
    }
  }
  $("#submitCreateGroupBtn").click(async () => {
    const name = $("#groupName").val().trim();
    $("#groupNameError,#groupEmailError,#groupFriendsError").text("");
    if (!name || name.length > 50) {
      $("#groupNameError").text("Required, max 50 chars");
      return $("#groupName").addClass("is-invalid");
    }
    if (!groupEmails.length && !groupFriendIDs.length) {
      $("#groupEmailError,#groupFriendsError").text(
        "Add at least one email or friend"
      );
      return;
    }
    const btn = $("#submitCreateGroupBtn").get(0);
    addSpinnerToButton(btn);
    try {
      await fetch(API + "mailing_list", {
        // VVV
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          initiatorId: userID,
          recipientsEmails: groupEmails,
          recipientsIds: groupFriendIDs,
        }),
      });
      createPopup("Group created!");
      createModal.hide();
    } catch {
      createPopupError("Could not create group");
    } finally {
      restoreButton(btn);
    }
  });

  //////////////////////////////// SHARE LINK MODAL ///////////////////////////

  let shareEmails = [],
    shareGroupIDs = [], // This array will hold the IDs of selected groups
    shareFriendIDs = [];
  let availableGroups = []; // This will cache the fetched groups {ListId, ListName}

  $("#shareLinkBtn").click(async () => {
    if (!userID) return createPopupWarning("Please log in to share a link!");
    // Reset all states
    shareEmails = [];
    shareGroupIDs = [];
    shareFriendIDs = [];
    availableGroups = [];

    // Reset all UI elements
    $(
      "#shareLinkError,#shareGroupError,#shareFriendsError,#shareEmailError"
    ).text("");
    $("#shareEmailInput").val("");
    $("#groupSearchInput").val("");
    $("#selectedGroupPills").empty();
    renderShareEmailList();

    // Set loading indicators
    const $shareLinkSelect = $("#shareLinkSelect");
    $shareLinkSelect
      .empty()
      .append('<option value="">-- loading links... --</option>');
    $("#shareFriendsList")
      .empty()
      .append('<small class="text-muted">Loading friends...</small>');

    shareModal.show();

    try {
      // Fetch all data concurrently
      const fetchLinks = fetch(API_URL + "users/get-user-links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ UserId: userID }), // Note: Your file uses 'UserId' here
      }).then((res) => res.json());
      // console.log(fetchLinks);

      // Fetching groups as you specified
      const fetchGroups = fetch(API_URL + "users/get-users-mailing-lists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ InitiatorId: userID }),
      }).then((res) => res.json());

      const fetchFriends = fetch(API_URL + "users/get-user-friends", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ UserId: userID }), // Note: Your file uses 'UserId' here
      }).then((res) => res.json());

      const [links, groups, friends] = await Promise.all([
        fetchLinks,
        fetchGroups,
        fetchFriends,
      ]);
      console.log("Links:", links);
      console.log("Groups:", groups);
      console.log("Friends:", friends);
      // --- Populate UI with fetched data ---

      $shareLinkSelect
        .empty()
        .append('<option value="">-- choose link --</option>');

      userLinks = links.links;
      console.log("links:", links);
      console.log("User Links:", userLinks);

      if (userLinks && userLinks.length > 0) {
        userLinks.forEach((l) => {
          console.log("Link:", l);
          $shareLinkSelect.append(
            `<option value="${l.LinkId}">${l.Name}</option>`
          );
        });
      } else {
        $shareLinkSelect
          .empty()
          .append('<option value="">-- no links found --</option>');
      }

      // Populate friends list using the original function
      //renderShareFriendsList(friends || []);

      const friendsList = Array.isArray(friends)
        ? friends
        : friends.friends || [];

      renderShareFriendsList(friendsList);

      // Initialize the new group selector UI
      availableGroups = groups || [];
      renderGroupDatalist(availableGroups);

      // const friendsList = Array.isArray(friendsResponse)
      //   ? friendsResponse
      //   : friendsResponse.friends || [];
      // renderShareFriendsList(friendsList);
    } catch (error) {
      console.error("Failed to load data for sharing:", error);
      createPopupError("Could not load your data. Please try again.");
      shareModal.hide();
    }
  });

  // --- Group Selection Logic ---

  // Renders the <datalist> for autocomplete suggestions
  function renderGroupDatalist(groups) {
    const $datalist = $("#groupDatalist").empty();
    if (!groups || groups.length === 0) {
      $("#groupSearchInput").attr("placeholder", "No groups found.");
      return;
    }
    $("#groupSearchInput").attr("placeholder", "Type to search for a group...");
    groups.forEach((g) => {
      // The user sees the ListName in the dropdown
      $datalist.append(`<option value="${g.ListName}">`);
    });
  }

  // Renders the visual "pills" for the groups that have been selected
  function renderSelectedGroupPills() {
    const $container = $("#selectedGroupPills").empty();
    // Find the full group objects that correspond to the selected IDs
    const selectedGroups = availableGroups.filter((g) =>
      shareGroupIDs.includes(g.ListId)
    );

    selectedGroups.forEach((g) => {
      const $pill = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${g.ListName}
          <button type="button" class="btn-close btn-close-white btn-sm ms-2" data-id="${g.ListId}"></button>
        </span>`);
      $container.append($pill);
    });
  }

  // Event handler for when a user selects a group from the dropdown
  $("#groupSearchInput").on("change", function () {
    const selectedName = $(this).val();
    const selectedGroup = availableGroups.find(
      (g) => g.ListName === selectedName
    );

    if (selectedGroup) {
      // Add the group's ID to our array if it's not already there
      if (!shareGroupIDs.includes(selectedGroup.ListId)) {
        shareGroupIDs.push(selectedGroup.ListId);
        renderSelectedGroupPills(); // Update the UI
      }
      // Clear the input field for the next selection
      $(this).val("");
    }
  });

  // Event handler for removing a group by clicking the 'x' on a pill
  $("#selectedGroupPills").on("click", ".btn-close", function () {
    const groupIdToRemove = $(this).data("id").toString();
    shareGroupIDs = shareGroupIDs.filter((id) => id !== groupIdToRemove);
    renderSelectedGroupPills(); // Update the UI
  });

  // --- Email and Friend Selection Logic (Unchanged from your file) ---

  $("#addShareEmailBtn").click(() => {
    const val = $("#shareEmailInput").val().trim().toLowerCase();
    $("#shareEmailError").text("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val))
      return $("#shareEmailError").text("Enter a valid email");
    if (shareEmails.includes(val))
      return $("#shareEmailError").text("Already added");
    shareEmails.push(val);
    $("#shareEmailInput").val("");
    renderShareEmailList();
  });

  function renderShareEmailList() {
    // This function is unchanged from your file
    const $c = $("#shareEmailList").empty();
    shareEmails.forEach((e) => {
      const $chip = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${e}
          <button type="button" class="btn-close btn-close-white btn-sm ms-2"></button>
        </span>`);
      $chip.find("button").click(() => {
        shareEmails = shareEmails.filter((x) => x !== e);
        renderShareEmailList();
      });
      $c.append($chip);
    });
  }

  function renderShareFriendsList(friends) {
    // This function is unchanged from your file
    const $c = $("#shareFriendsList").empty();
    if (!Array.isArray(friends) || friends.length === 0) {
      $c.append('<small class="text-muted">No friends added yet.</small>');
      return;
    }
    friends.forEach((f) => {
      const $lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center" style="cursor:pointer;">
          <input type="checkbox" class="form-check-input me-1" value="${f.UserId}">
          <img src="${f.Picture}" width="24" height="24" class="rounded-circle">
          <span class="ms-1">${f.Username}</span>
        </label>`);
      $lbl.find("input").on("change", function () {
        const id = this.value;
        if (this.checked) shareFriendIDs.push(id);
        else shareFriendIDs = shareFriendIDs.filter((x) => x !== id);
      });
      $c.append($lbl);
    });
  }

  $("#submitShareLinkBtn").click(async () => {
    // The future lambda call will use the 'shareGroupIDs', 'shareFriendIDs', and 'shareEmails' arrays.
    const linkID = $("#shareLinkSelect").val();
    $(
      "#shareLinkError,#shareGroupError,#shareFriendsError,#shareEmailError"
    ).text("");
    if (!linkID) {
      return $("#shareLinkError").text("Pick a link");
    }
    if (
      !shareGroupIDs.length &&
      !shareFriendIDs.length &&
      !shareEmails.length
    ) {
      $("#shareGroupError,#shareFriendsError,#shareEmailError").text(
        "Add at least one group, friend or email"
      );
      return;
    }
    const btn = $("#submitShareLinkBtn").get(0);
    addSpinnerToButton(btn);

    console.log(linkID);
    const body = {
      senderId: userID,
      linkId: linkID,
      groupIds: shareGroupIDs,
      friendIds: shareFriendIDs,
      recipientsEmails: shareEmails,
      site: window.location.origin + "/main/redirect.html?code=" + linkID, // Include the site URL for the email body
    };
    console.log("Sharing link with body:", body);
    try {
      await fetch(API_URL + "mail", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      createPopup("Link shared!");
      shareModal.hide();
    } catch {
      createPopupError("Could not share link");
    } finally {
      restoreButton(btn);
    }
  });
});
