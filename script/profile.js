$(document).ready(async function () {
  const params = new URLSearchParams(window.location.search);
  const profileID = params.get("userID");
  const me = localStorage.getItem("userID");
  const isOwner = profileID === me;

  try {
    const resp = await fetch(API + `Users/byid?userID=${profileID}`);
    const body = await resp.json();
    const data =
      typeof body.body === "string" ? JSON.parse(body.body) : body.body;

    $("#userName").text(`User name: ${data.username}`);
    $("#user-name").text(`Full Name: ${data.name}`);
    $("#user-joined").text(
      `Date Joined: ${new Date(data.creationDate).toLocaleDateString()}`
    );
    $("#address").text(`Address: ${data.address}`);
    $("#phone-number").text(
      `Phone Number: ${formatPhoneNumber(data.phone_number)}`
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
    const resp = await fetch(API + `Links/created?userID=${profileID}`);
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

  const linkModal = new bootstrap.Modal($("#linkDetailModal"));
  let selectedLinkId;

  // 6.1) Row‐click opens modal
  $("#linksTable tbody").on("click", "tr", async function () {
    const rowData = $("#linksTable").DataTable().row(this).data();
    if (!isOwner || !rowData) return;
    selectedLinkId = rowData.linkID; // assumes your link object has `linkID`
    $("#linkDetailModalLabel").text(rowData.name);

    // fetch detail from server
    try {
      const resp = await fetch(API + `Links/details?linkId=${selectedLinkId}`);
      const j = await resp.json();
      const info = typeof j.body === "string" ? JSON.parse(j.body) : j.body;

      // populate stats
      const statsUl = $("#countryStats").empty();
      Object.entries(info.clicksByCountry || {}).forEach(([country, count]) => {
        statsUl.append(`<li>${country}: ${count}</li>`);
      });

      // password & toggle button
      $("#linkPassword")
        .val(info.password || "")
        .prop("disabled", true);
      $("#togglePasswordBtn").text(info.password ? "Edit" : "Add");

      // visibility switch
      $("#linkVisibilitySwitch").prop("checked", info.isPublic);

      $("#linkPasswordError").text("");
      linkModal.show();
    } catch (e) {
      console.error(e);
      createPopupError("Could not load link details");
    }
  });

  // Toggle password field edit/save
  $("#togglePasswordBtn").click(() => {
    const pwd = $("#linkPassword");
    const editing = pwd.prop("disabled");
    pwd.prop("disabled", !editing);
    $(this).text(editing ? "Save" : "Edit");
  });

  // Save changes (password & visibility)
  $("#saveLinkChangesBtn").click(async () => {
    const newPassword = $("#linkPassword").val().trim() || null;
    const isPublic = $("#linkVisibilitySwitch").prop("checked");
    const btn = $("#saveLinkChangesBtn").get(0);
    addSpinnerToButton(btn);

    try {
      await fetch(API + "Links/update", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          linkId: selectedLinkId,
          password: newPassword,
          isPublic: isPublic,
        }),
      });
      createPopup("Saved changes");
      linkModal.hide();
      $("#linksTable").DataTable().ajax.reload(null, false);
    } catch (e) {
      console.error(e);
      createPopupError("Save failed");
    } finally {
      restoreButton(btn);
    }
  });

  // Delete link
  $("#deleteLinkBtn").click(async () => {
    if (!confirm("Delete this link permanently?")) return;
    const btn = $("#deleteLinkBtn").get(0);
    addSpinnerToButton(btn);

    try {
      await fetch(API + `Links/${selectedLinkId}`, { method: "DELETE" });
      createPopup("Link deleted");
      linkModal.hide();
      $("#linksTable").DataTable().row(".selected").remove().draw();
    } catch (e) {
      console.error(e);
      createPopupError("Delete failed");
    } finally {
      restoreButton(btn);
    }
  });

  // Generate & render 10 mock achievements
  const mockAchievements = Array.from({ length: 10 }, (_, i) => {
    const user = MOCK_USERS[i % MOCK_USERS.length];
    const daysAgo = Math.floor(Math.random() * 60);
    const earned = new Date(Date.now() - daysAgo * 86400000)
      .toISOString()
      .split("T")[0];
    return {
      username: user.username,
      picture: user.picture,
      linkName: `Sample Link ${i + 1}`,
      numberOfClicks: Math.floor(Math.random() * 500) + 1,
      dateEarned: earned,
    };
  });
  renderAchievements(mockAchievements);

  // Helper: render achievements cards
  function renderAchievements(list) {
    const container = $("#achievementsContainer").empty();
    list.forEach((a) => {
      const card = $(`
        <div class="achievement-card col-auto">
          <img src="${a.picture}" alt="${a.username}" />
          <div class="link-name">${a.linkName}</div>
          <div class="clicks">${a.numberOfClicks} clicks</div>
          <div class="date">${new Date(a.dateEarned).toLocaleDateString()}</div>
        </div>
      `);
      container.append(card);
    });
  }
});
