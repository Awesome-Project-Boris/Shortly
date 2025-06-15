$(document).ready(function () {
  if (!$.fn.DataTable) {
    console.error("DataTables not loaded");
    return;
  }

  const table = $("#linksTable").DataTable({
    responsive: true,
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

  const q = localStorage.getItem("searchQuery");
  if (q) {
    table.search(q).draw();
    localStorage.removeItem("searchQuery");
  }

  const userID = currentUserID;

  $("#newLinkBtn").click(() => {
    // if (!userID) return createPopupWarning("Please log in to add a link");                          // TEMP
    window.location.href = "new_item.html";
  });

  $("#friendsBtn").click(() => {
    // if (!userID) return createPopupWarning("Please log in to view friends");                          // TEMP
    window.location.href = "social.html";
  });

  $("#createGroupBtn").click(() => {
    //  if (!userID) return createPopupWarning("Please log in to create groups");                          // TEMP
    openCreateModal();
  });

  $("#shareLinkBtn").click(() => {
    // if (!userID) return createPopupWarning("Please log in to share links");                          // TEMP
    openShareModal();
  });


  const createModal = new bootstrap.Modal($("#createGroupModal"));
  let groupEmails = [];
  let groupFriendIDs = [];

  async function openCreateModal() {
    $("#groupName").val("").removeClass("is-invalid");
    $("#groupNameError, #groupFriendsError").text("");
    $("#groupNameCounter").text("0/50");
    $("#groupEmailInput").val("");
    groupEmails = [];
    groupFriendIDs = [];
    renderGroupEmailList();


    let friends = window.MOCK_FRIENDS || [];
    if (!friends.length) {
      try {
        const resp = await fetch(API + `Friends/list?userID=${userID}`);
        const json = await resp.json();
        friends =
          typeof json.body === "string" ? JSON.parse(json.body) : json.body;
      } catch {}
    }
    renderGroupFriendsList(friends);

    createModal.show();
  }

  $("#groupName").on("input", function () {
    const len = this.value.length;
    $("#groupNameCounter").text(`${len}/50`);
    $("#groupNameError").text("");
    $(this).toggleClass("is-invalid", len === 0 || len > 50);
  });

  $("#addGroupEmailBtn").click(() => {
    const val = $("#groupEmailInput").val().trim().toLowerCase();
    $("#groupEmailError").text("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
      return $("#groupEmailError").text("Enter a valid email");
    }
    if (groupEmails.includes(val)) {
      return $("#groupEmailError").text("Already added");
    }
    groupEmails.push(val);
    $("#groupEmailInput").val("");
    renderGroupEmailList();
  });

  function renderGroupEmailList() {
    const c = $("#groupEmailList").empty();
    groupEmails.forEach((email) => {
      const chip = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${email}
          <button type="button"
                  class="btn-close btn-close-white btn-sm ms-2"></button>
        </span>`);
      chip.find("button").click(() => {
        groupEmails = groupEmails.filter((e) => e !== email);
        renderGroupEmailList();
      });
      c.append(chip);
    });
  }

  function renderGroupFriendsList(friends) {
    const c = $("#groupFriendsList").empty();
    friends.forEach((f) => {
      const lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox"
                 class="form-check-input me-1"
                 value="${f.userID}" />
          <img src="${f.picture}"
               class="rounded-circle"
               width="24" height="24" />
          <span class="ms-1">${f.username}</span>
        </label>`);
      lbl.find("input").on("change", function () {
        const id = this.value;
        if (this.checked) groupFriendIDs.push(id);
        else groupFriendIDs = groupFriendIDs.filter((x) => x !== id);
      });
      c.append(lbl);
    });
  }

  $("#submitCreateGroupBtn").click(async () => {
    const name = $("#groupName").val().trim();
    $("#groupNameError, #groupFriendsError").text("");
    if (!name || name.length > 50) {
      $("#groupNameError").text("Required, max 50 chars");
      return $("#groupName").addClass("is-invalid");
    }
    if (!groupEmails.length && !groupFriendIDs.length) {
      $("#groupEmailError").text("Add at least one email or friend");
      $("#groupFriendsError").text("Add at least one email or friend");
      return;
    }
    const btn = $("#submitCreateGroupBtn").get(0);
    addSpinnerToButton(btn);
    try {
      await fetch(API + "Groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          initiatorId: currentUserID,
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


  const shareModal = new bootstrap.Modal($("#shareLinkModal"));
  let shareEmails = [];
  let shareGroupIDs = [];
  let shareFriendIDs = [];

  async function openShareModal() {
    shareEmails = [];
    shareGroupIDs = [];
    shareFriendIDs = [];
    renderShareEmailList();
    $(
      "#shareLinkError, #shareGroupError, #shareFriendsError, #shareEmailError"
    ).text("");

    const linkSel = $("#shareLinkSelect")
      .empty()
      .append("<option>Loading…</option>");
    try {
      const resp = await fetch(API + `Links/created?userID=${userID}`);
      const j = await resp.json();
      const ls = typeof j.body === "string" ? JSON.parse(j.body) : j.body;
      linkSel.empty().append('<option value="">-- choose link --</option>');
      ls.forEach((l) =>
        linkSel.append(`<option value="${l.linkID}">${l.name}</option>`)
      );
    } catch {
      linkSel.empty().append("<option>(failed to load)</option>");
    }

    let groups = window.MOCK_GROUPS || [];
    try {
      const r = await fetch(API + `Groups/list?initiatorId=${userID}`);
      const d = await r.json();
      groups = typeof d.body === "string" ? JSON.parse(d.body) : d.body;
    } catch {}
    renderShareGroupList(groups);

    let friends = window.MOCK_FRIENDS || [];
    try {
      const r = await fetch(API + `Friends/list?userID=${userID}`);
      const d = await r.json();
      friends = typeof d.body === "string" ? JSON.parse(d.body) : d.body;
    } catch {}
    renderShareFriendsList(friends);

    shareModal.show();
  }

  $("#addShareEmailBtn").click(() => {
    const val = $("#shareEmailInput").val().trim().toLowerCase();
    $("#shareEmailError").text("");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)) {
      return $("#shareEmailError").text("Enter a valid email");
    }
    if (shareEmails.includes(val)) {
      return $("#shareEmailError").text("Already added");
    }
    shareEmails.push(val);
    $("#shareEmailInput").val("");
    renderShareEmailList();
  });

  function renderShareEmailList() {
    const c = $("#shareEmailList").empty();
    shareEmails.forEach((email) => {
      const chip = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${email}
          <button type="button" class="btn-close btn-close-white btn-sm ms-2"></button>
        </span>`);
      chip.find("button").click(() => {
        shareEmails = shareEmails.filter((e) => e !== email);
        renderShareEmailList();
      });
      c.append(chip);
    });
  }

  function renderShareGroupList(groups) {
    const c = $("#shareGroupList").empty();
    groups.forEach((g) => {
      const lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox"
                 class="form-check-input me-1"
                 value="${g.groupID}" />
          <span class="ms-1">${g.name}</span>
        </label>`);
      lbl.find("input").on("change", function () {
        const id = this.value;
        if (this.checked) shareGroupIDs.push(id);
        else shareGroupIDs = shareGroupIDs.filter((x) => x !== id);
      });
      c.append(lbl);
    });
  }

  function renderShareFriendsList(friends) {
    const c = $("#shareFriendsList").empty();
    friends.forEach((f) => {
      const lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox"
                 class="form-check-input me-1"
                 value="${f.userID}" />
          <img src="${f.picture}"
               class="rounded-circle"
               width="24" height="24" />
          <span class="ms-1">${f.username}</span>
        </label>`);
      lbl.find("input").on("change", function () {
        const id = this.value;
        if (this.checked) shareFriendIDs.push(id);
        else shareFriendIDs = shareFriendIDs.filter((x) => x !== id);
      });
      c.append(lbl);
    });
  }

  $("#submitShareLinkBtn").click(async () => {
    const linkID = $("#shareLinkSelect").val();
    $(
      "#shareLinkError, #shareGroupError, #shareFriendsError, #shareEmailError"
    ).text("");

    if (!linkID) {
      return $("#shareLinkError").text("Pick a link");
    }
    if (
      !shareGroupIDs.length &&
      !shareFriendIDs.length &&
      !shareEmails.length
    ) {
      $("#shareGroupError").text("Add at least one group, friend or email");
      return;
    }

    const btn = $("#submitShareLinkBtn").get(0);
    addSpinnerToButton(btn);
    try {
      await fetch(API + "Links/share", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          senderId: userID,
          linkId: linkID,
          groupIds: shareGroupIDs,
          friendIds: shareFriendIDs,
          recipientsEmails: shareEmails,
        }),
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
