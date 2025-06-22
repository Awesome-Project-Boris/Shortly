// index.js
$(document).ready(async function() {
  const userID = localStorage.getItem("userID");
  const API_URL = API; // Assuming 'API' is defined in global.js

  const globalSearchQuery = localStorage.getItem("searchQuery") || "";
  // Clear the stored query so it doesn't affect the next page load
  if (globalSearchQuery) {
    localStorage.removeItem("searchQuery");
  }

  $('#linksTable').bootstrapTable({
    data: window.MOCK_LINKS || [], // Use the mock data from mockUsers.js
    //url: `${API_URL}/links`, // Use the actual API URL for server-side data
    classes: 'table-striped table-hover',
    pagination: true,
    pageSize: 20, // A page size of 20 is more typical for client-side data
    search: true, // Enable the in-table search
    // Pre-fill the in-table search with the query from the global nav search
    searchText: globalSearchQuery,
    searchOnEnterKey: false,
    searchTimeOut: 300,
    escape: false,
    columns: [{
      field: 'name',
      title: 'Link name'
    }, {
      field: 'description',
      title: 'Description'
    }, {
      field: 'shortUrl',
      title: 'Link',
      formatter: (value, row) => `<a href="#">${value}</a>` // Use # for mock links
    }, {
      field: 'isProtected',
      title: '<img src="../media/lock.png" width="16" alt="Protected">',
      align: 'center',
      width: 40,
      formatter: (value) => value ? '<img src="../media/lock.png" width="16" alt="Protected">' : ''
    }],
    onClickRow: function(row) {
      if (String(row.ownerId) === userID) {
        // For mock data, we can't really navigate. You might show an alert.
        alert(`Navigating to your link: ${row.shortUrl}`);
        return;
      }
      // The modal logic for non-owners remains the same
      $('#linkAccessLabel').text(row.name);
      $('#accessDescription').text(row.description);
      if (row.isProtected) {
        $('#passwordGroup').show();
        $('#accessPassword').val('');
      } else {
        $('#passwordGroup').hide();
      }
      $('#accessError').text('');
      window._currentShortUrl = row.shortUrl;
      window._needsPassword = row.isProtected;
      new bootstrap.Modal($('#linkAccessModal')[0]).show();
    }
  });

  // Go→Link button
  $('#goToLinkBtn').click(function() {
    const pw = $('#accessPassword').val().trim();
    if (window._needsPassword && !pw) {
      return $('#accessError').text('Password required');
    }
    $('#linkAccessModal').modal('hide');
    window.location.href = window._needsPassword
      ? `${window._currentShortUrl}?pw=${encodeURIComponent(pw)}`
      : window._currentShortUrl;
  });

  // action buttons
  $('#newLinkBtn').click(() => {
    if (!userID) return createPopupWarning('Please log in to add a link');
    window.location.href = 'new_item.html';
  });
  $('#friendsBtn').click(() => {
    if (!userID) return createPopupWarning('Please log in to view friends');
    window.location.href = 'social.html';
  });

  // modals
  const createModal = new bootstrap.Modal($('#createGroupModal')[0]);
  const shareModal  = new bootstrap.Modal($('#shareLinkModal')[0]);

  // CREATE GROUP
  let groupEmails    = [], groupFriendIDs = [];
  $('#createGroupBtn').click(function() {
    groupEmails = [];
    groupFriendIDs = [];
    $('#groupName').val('').removeClass('is-invalid');
    $('#groupNameError,#groupEmailError,#groupFriendsError').text('');
    $('#groupNameCounter').text('0/50');
    $('#groupEmailInput').val('');
    renderGroupEmailList();
    renderGroupFriendsList(window.MOCK_FRIENDS || []);
    createModal.show();
  });

  $('#groupName').on('input', function() {
    const len = this.value.length;
    $('#groupNameCounter').text(`${len}/50`);
    $(this).toggleClass('is-invalid', !len || len>50);
  });
  $('#addGroupEmailBtn').click(() => {
    const val = $('#groupEmailInput').val().trim().toLowerCase();
    $('#groupEmailError').text('');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val))
      return $('#groupEmailError').text('Enter a valid email');
    if (groupEmails.includes(val))
      return $('#groupEmailError').text('Already added');
    groupEmails.push(val);
    $('#groupEmailInput').val('');
    renderGroupEmailList();
  });
  function renderGroupEmailList() {
    const $c = $('#groupEmailList').empty();
    groupEmails.forEach(e => {
      const $chip = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${e}
          <button type="button" class="btn-close btn-close-white btn-sm ms-2"></button>
        </span>`);
      $chip.find('button').click(()=> {
        groupEmails = groupEmails.filter(x=>x!==e);
        renderGroupEmailList();
      });
      $c.append($chip);
    });
  }
  function renderGroupFriendsList(friends) {
    const $c = $('#groupFriendsList').empty();
    friends.forEach(f => {
      const $lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox" class="form-check-input me-1" value="${f.userID}">
          <img src="${f.picture}" width="24" height="24" class="rounded-circle">
          <span class="ms-1">${f.username}</span>
        </label>`);
      $lbl.find('input').on('change', function() {
        const id = this.value;
        if (this.checked) groupFriendIDs.push(id);
        else groupFriendIDs = groupFriendIDs.filter(x=>x!==id);
      });
      $c.append($lbl);
    });
  }
  $('#submitCreateGroupBtn').click(async () => {
    const name = $('#groupName').val().trim();
    $('#groupNameError,#groupEmailError,#groupFriendsError').text('');
    if (!name || name.length>50) {
      $('#groupNameError').text('Required, max 50 chars');
      return $('#groupName').addClass('is-invalid');
    }
    if (!groupEmails.length && !groupFriendIDs.length) {
      $('#groupEmailError,#groupFriendsError').text('Add at least one email or friend');
      return;
    }
    const btn = $('#submitCreateGroupBtn').get(0);
    addSpinnerToButton(btn);
    try {
      await fetch(API+'Groups', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          name,
          initiatorId: userID,
          recipientsEmails: groupEmails,
          recipientsIds:   groupFriendIDs
        })
      });
      createPopup('Group created!');
      createModal.hide();
    } catch {
      createPopupError('Could not create group');
    } finally {
      restoreButton(btn);
    }
  });

  // SHARE LINK
  let shareEmails = [], shareGroupIDs = [], shareFriendIDs = [];
  $('#shareLinkBtn').click(() => {
    shareEmails = []; shareGroupIDs = []; shareFriendIDs = [];
    $('#shareLinkError,#shareGroupError,#shareFriendsError,#shareEmailError').text('');
    $('#shareLinkSelect').empty().append('<option>Loading…</option>');
    // load links
    let links = window.MOCK_LINKS || [];
    $('#shareLinkSelect').empty().append('<option value="">-- choose link --</option>');
    links.forEach(l => {
      $('#shareLinkSelect').append(`<option value="${l.linkID}">${l.name}</option>`);
    });
    renderShareGroupList(window.MOCK_GROUPS || []);
    renderShareFriendsList(window.MOCK_FRIENDS || []);
    shareModal.show();
  });
  $('#addShareEmailBtn').click(()=>{
    const val = $('#shareEmailInput').val().trim().toLowerCase();
    $('#shareEmailError').text('');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val))
      return $('#shareEmailError').text('Enter a valid email');
    if (shareEmails.includes(val))
      return $('#shareEmailError').text('Already added');
    shareEmails.push(val);
    $('#shareEmailInput').val('');
    renderShareEmailList();
  });
  function renderShareEmailList() {
    const $c = $('#shareEmailList').empty();
    shareEmails.forEach(e => {
      const $chip = $(`
        <span class="badge bg-primary d-flex align-items-center">
          ${e}
          <button type="button" class="btn-close btn-close-white btn-sm ms-2"></button>
        </span>`);
      $chip.find('button').click(()=>{
        shareEmails = shareEmails.filter(x=>x!==e);
        renderShareEmailList();
      });
      $c.append($chip);
    });
  }
  function renderShareGroupList(groups) {
    const $c = $('#shareGroupList').empty();
    groups.forEach(g=>{
      const $lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox" class="form-check-input me-1" value="${g.groupID}">
          <span class="ms-1">${g.name}</span>
        </label>`);
      $lbl.find('input').on('change',function(){
        const id=this.value;
        if(this.checked) shareGroupIDs.push(id);
        else shareGroupIDs = shareGroupIDs.filter(x=>x!==id);
      });
      $c.append($lbl);
    });
  }
  function renderShareFriendsList(friends) {
    const $c = $('#shareFriendsList').empty();
    friends.forEach(f=>{
      const $lbl = $(`
        <label class="badge bg-light text-dark d-flex align-items-center">
          <input type="checkbox" class="form-check-input me-1" value="${f.userID}">
          <img src="${f.picture}" width="24" height="24" class="rounded-circle">
          <span class="ms-1">${f.username}</span>
        </label>`);
      $lbl.find('input').on('change',function(){
        const id=this.value;
        if(this.checked) shareFriendIDs.push(id);
        else shareFriendIDs = shareFriendIDs.filter(x=>x!==id);
      });
      $c.append($lbl);
    });
  }
  $('#submitShareLinkBtn').click(async ()=>{
    const linkID = $('#shareLinkSelect').val();
    $('#shareLinkError,#shareGroupError,#shareFriendsError,#shareEmailError').text('');
    if(!linkID) {
      return $('#shareLinkError').text('Pick a link');
    }
    if(!shareGroupIDs.length && !shareFriendIDs.length && !shareEmails.length) {
      $('#shareGroupError,#shareFriendsError,#shareEmailError')
        .text('Add at least one group, friend or email');
      return;
    }
    const btn = $('#submitShareLinkBtn').get(0);
    addSpinnerToButton(btn);
    try {
      await fetch(API+'Links/share',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          senderId:         userID,
          linkId:           linkID,
          groupIds:         shareGroupIDs,
          friendIds:        shareFriendIDs,
          recipientsEmails: shareEmails
        })
      });
      createPopup('Link shared!');
      shareModal.hide();
    } catch {
      createPopupError('Could not share link');
    } finally {
      restoreButton(btn);
    }
  });

});

async function handleProtectedLinkClick(linkData) {
    // NOTE: Ensure the modal HTML from the previous step is in your index.html
    const passwordModal = new bootstrap.Modal(document.getElementById('passwordAccessModal'));
    const passwordInput = $('#accessPasswordInput');
    const errorMsg = $('#passwordAccessError');
    const unlockBtn = $('#unlockLinkBtn');

    // Reset modal state for a clean appearance
    passwordInput.val('').removeClass('is-invalid');
    errorMsg.text('');
    passwordModal.show();

    // Attach a one-time click handler to the unlock button to prevent multiple submissions
    unlockBtn.off('click').on('click', async function() {
        const password = passwordInput.val();
        if (!password) {
            errorMsg.text('Password cannot be empty.');
            passwordInput.addClass('is-invalid');
            return;
        }

        addSpinnerToButton(this);
        errorMsg.text('');
        passwordInput.removeClass('is-invalid');

        try {
            const resp = await fetch(API + 'links/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    linkId: linkData.LinkId || linkData.linkID, // Handle both casing conventions
                    password: password
                })
            });
            const result = await resp.json();

            if (result.accessGranted) {
                passwordModal.hide();
                // Redirect to the original URL provided by the server
                window.location.href = result.originalUrl;
            } else {
                errorMsg.text(result.message || 'Incorrect password.');
                passwordInput.addClass('is-invalid');
            }
        } catch (e) {
            console.error('Password verification failed:', e);
            errorMsg.text('An error occurred. Please try again.');
        } finally {
            restoreButton(this);
        }
    });
}
