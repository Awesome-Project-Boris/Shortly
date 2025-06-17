$(document).ready(async function () {
  const params = new URLSearchParams(window.location.search);
  const profileID = params.get("userID");
  const me = localStorage.getItem("userID");
  const isOwner = profileID === me;

  try {
    const resp = await fetch(API + 'Users/byid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: profileID })
    });
    const body = await resp.json();
    const data = typeof body.body === "string" ? JSON.parse(body.body) : body.body;

    $("#userName").text(`User name: ${data.username}`);
    $("#user-name").text(`Full Name: ${data.name}`);
    $("#user-joined").text(
      `Date Joined: ${new Date(data.creationDate).toLocaleDateString()}`
    );
    $("#user-items-count").text(`Links created: ${data.linkCount ?? 0}`);
    $(".profile-pic").attr("src", data.picture);
  } catch (e) {
    console.error("Failed to load profile:", e);
  }

  if (!isOwner && me) {
    $("#friendRequestBtn")
      .show()
      .on("click", async function () {
        const $btn = $(this);
        addSpinnerToButton(this);
        try {
          const res = await fetch(API + "Friends/request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fromUserID: me, toUserID: profileID }),
          });
          if (!res.ok) throw new Error();
          createPopup("Friend request sent!");
          $btn.text("Request Sent");
        } catch {
          createPopupError("Could not send friend request.");
          restoreButton(this);
        }
      });
  }

  // Fetch & render links DataTable
  let links = [];
  try {
    const resp = await fetch(API + 'Links/created', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userId: profileID })
    });
    const body = await resp.json();
    links = JSON.parse(body.body);
  } catch (e) {
    console.error("Failed to load links:", e);
  }

  const columns = [
    { data: "name", title: "Link name" },
    { data: "description", title: "Description" },
    {
      data: "shortUrl",
      title: "Link",
      render: (u) => `<a href="${u}" target="_blank">${u}</a>`,
    },
  ];
  if (isOwner) {
    columns.push({
      data: "isPublic",
      title: "Visible/Private",
      render: (v) => (v ? "Public" : "Private"),
    });

    // only retitle the *first* section header (the links one)
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
    language: {
      search: "_INPUT_",
      searchPlaceholder: "Filter links...",
    },
  });

  // ─────────────────────────────────────────────
  // 6) LINK‐DETAILS MODAL (owner only)
  // ─────────────────────────────────────────────

  // WE ASSUME WE GET THIS FROM THE SERVER:

  // {
  //   clicksByCountry: { "USA": 123, "Canada": 45, … },
  //   password:        "hunter2" | null,
  //   isPublic:        true|false
  // }

  const linkModal = new bootstrap.Modal(document.getElementById('linkDetailModal'));
let selectedLink = null; // Store the entire link object
const currentUserID = localStorage.getItem("userID"); // Get the logged-in user's ID

// --- Open Modal on Row Click ---
$('#linksTable tbody').on('click', 'tr', async function () {
    const rowData = $('#linksTable').DataTable().row(this).data();
    if (!isOwner || !rowData) return;

    selectedLink = rowData; // Store the whole link object for later use
    $('#linkDetailModalLabel').text(selectedLink.name);

    try {
        const resp = await fetch(API + 'Links/details', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ linkId: selectedLink.LinkId })
        });
        if (!resp.ok) throw new Error('Failed to fetch link details');
        const info = await resp.json();

        // Populate click stats
        const statsUl = $('#countryStats').empty();
        const countries = info.clicksByCountry || {};
        if (Object.keys(countries).length > 0) {
            Object.entries(countries).forEach(([country, count]) => {
                statsUl.append(`<li>${country}: ${count}</li>`);
            });
        } else {
            statsUl.append(`<li class="text-muted">No clicks recorded yet.</li>`);
        }
        
        // Set visibility switch
        $('#linkVisibilitySwitch').prop('checked', info.isPublic);
        
        // Manage password section visibility
        if (info.isPasswordProtected) {
            $('#passwordSection').show();
            // Store the real password securely on an element for the reveal feature
            $('#revealedPasswordText').data('password', info.password || '');
        } else {
            $('#passwordSection').hide();
        }
        
        // Reset all modal fields and states on open
        $('#currentPassword, #newPassword').val('');
        $('#passwordUpdateError').text('');
        $('#revealedPassword').hide();

        linkModal.show();

    } catch (e) {
        console.error("Error loading link details:", e);
        createPopupError("Could not load link details.");
    }
});

// --- Save Visibility Changes ---
$('#saveLinkChangesBtn').click(async function () {
    const isPublic = $('#linkVisibilitySwitch').prop('checked');
    const btn = this;
    addSpinnerToButton(btn);

    try {
        // This should call your 'update_link_privacy' or 'toggle_link_privacy' Lambda
        const resp = await fetch(API + 'Links/privacy', { // Assuming endpoint name
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                linkId: selectedLink.linkID,
                isPrivate: !isPublic // isPublic is the opposite of IsPrivate
            }),
        });
        if (!resp.ok) throw new Error('Failed to update visibility.');
        
        createPopup('Visibility updated!');
        linkModal.hide();
        // You may need to refresh your DataTable to see the change
        $('#linksTable').DataTable().ajax.reload(null, false);
    } catch (e) {
        console.error("Save visibility failed:", e);
        createPopupError('Could not save visibility.');
    } finally {
        restoreButton(btn);
    }
});

// --- Change Password ---
$('#changePasswordBtn').click(async function() {
    const currentPassword = $('#currentPassword').val();
    const newPassword = $('#newPassword').val();
    const btn = this;

    // Basic validation
    if (!currentPassword || !newPassword) {
        $('#passwordUpdateError').text('Both fields are required.');
        return;
    }
    if (newPassword.length < 4) {
        $('#passwordUpdateError').text('New password must be at least 4 characters.');
        return;
    }
    
    $('#passwordUpdateError').text('');
    addSpinnerToButton(btn);

    try {
        const resp = await fetch(API + 'Links/password', { // Assuming endpoint from previous step
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                linkId: selectedLink.linkID,
                userId: currentUserID,
                currentPassword: currentPassword,
                newPassword: newPassword,
            }),
        });

        const result = await resp.json();
        
        if (!resp.ok) {
            // Use the error message from the Lambda function
            throw new Error(result.message || 'An unknown error occurred.');
        }

        createPopup('Password changed successfully!');
        $('#currentPassword, #newPassword').val(''); // Clear fields
        // Update the stored password for the reveal feature
        $('#revealedPasswordText').data('password', newPassword);

    } catch(e) {
        console.error("Password change failed:", e);
        $('#passwordUpdateError').text(e.message); // Show specific error
    } finally {
        restoreButton(btn);
    }
});


// --- Forgot/Reveal Password ---
$('#forgotPasswordBtn').click(function() {
    const storedPassword = $('#revealedPasswordText').data('password');
    if (storedPassword) {
        $('#revealedPasswordText').text(storedPassword);
        $('#revealedPassword').slideDown();
    }
});

// --- Delete Link ---
$('#deleteLinkBtn').click(async function () {
    const isConfirmed = await Swal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, delete it!'
    }).then((result) => result.isConfirmed);

    if (!isConfirmed) return;

    const btn = this;
    addSpinnerToButton(btn);

    try {
        const resp = await fetch(API + 'Links/delete', { 
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ linkId: selectedLink.LinkId })
        });
        if (!resp.ok) throw new Error('Delete request failed.');

        createPopup('Link deleted');
        linkModal.hide();
        // Remove the row from the DataTable without a full reload
        $('#linksTable').DataTable().row('.selected').remove().draw(false);
    } catch (e) {
        console.error('Delete failed:', e);
        createPopupError('Could not delete link.');
    } finally {
        restoreButton(btn);
    }
});
});
