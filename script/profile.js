$(document).ready(async function () {
    const params = new URLSearchParams(window.location.search);
    const profileID = params.get("userID");
    const me = localStorage.getItem("UserId");
    const isOwner = profileID === me;
    console.log(profileID)
    console.log(me)

    // This single API call now fetches the user's info, achievements, and links all at once.
    try {
        // NOTE: The endpoint name 'Users/profile' should match the API Gateway route for your new get_user_by_id_rewritten Lambda.
        const resp = await fetch(API + '/users/get-user-by-id', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // The request body now sends both the profile owner's ID and the logged-in user's ID.
            body: JSON.stringify({
                ProfileOwnerId: profileID,
                LoggedInUserId: me
            })
        });
        console.log(resp)

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
    const container = $('#achievementsContainer');
    if (!container.length) {
        console.error('Achievement container not found. Please add <div id="achievementsContainer" class="section"></div> to your HTML.');
        return;
    }

    container.empty(); // Clear previous content

    const title = $('<div class="section-header"><h3 class="section-title">Achievements</h3></div>');
    container.append(title);

    if (!achievements || achievements.length === 0) {
        container.append('<p class="text-muted">This user has not earned any achievements yet.</p>');
        return;
    }

    const list = $('<div class="achievements-list"></div>');
    achievements.forEach(ach => {
        // Here we assume the achievement object has a nested 'Achievement' object with the name
        const achievementName = ach.Achievement?.Name || `Achievement ${ach.AchievementId}`;
        const earnedDate = new Date(ach.DateEarned).toLocaleDateString();
        const achievementHtml = `
            <div class="achievement-item">
                <div class="achievement-icon"><i class="fas fa-trophy"></i></div>
                <div class="achievement-details">
                    <span class="achievement-name">${achievementName} on "${ach.LinkName}"</span>
                    <span class="achievement-date">Earned on ${earnedDate}</span>
                </div>
            </div>
        `;
        list.append(achievementHtml);
    });

    container.append(list);
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
        {
            data: "shortUrl", // Assuming this field exists on the link object
            title: "Link",
            render: (u) => u ? `<a href="${u}" target="_blank">${u}</a>` : 'N/A',
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
    const linkModal = new bootstrap.Modal(document.getElementById('linkDetailModal'));
    let selectedLink = null;
    const currentUserID = localStorage.getItem("userID");

    $('#linksTable tbody').on('click', 'tr', async function () {
        const rowData = $('#linksTable').DataTable().row(this).data();
        if (!isOwner || !rowData) return;

        selectedLink = rowData;
        $('#linkDetailModalLabel').text(`Statistics for "${selectedLink.Name}"`);

        $('#totalClicks').text('...');
        $('#countryStatsContainer').html('<div class="spinner-border spinner-border-sm text-primary" role="status"></div>');
        linkModal.show();

        try {
            const resp = await fetch(API + 'links/details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ linkId: selectedLink.LinkId })
            });
            if (!resp.ok) throw new Error('Failed to fetch link details');
            const info = await resp.json();

            $('#totalClicks').text(info.TotalClicks);
            renderCountryStats(info.clicksByCountry);

            $('#linkVisibilitySwitch').prop('checked', !info.IsPrivate);

            if (info.IsPasswordProtected) {
                $('#passwordSection').show();
                $('#revealedPasswordText').data('password', info.Password || '');
            } else {
                $('#passwordSection').hide();
            }

            $('#currentPassword, #newPassword').val('');
            $('#passwordUpdateError').text('');
            $('#revealedPassword').hide();

        } catch (e) {
            console.error("Error loading link details:", e);
            createPopupError("Could not load link details.");
            $('#countryStatsContainer').html('<p class="text-danger small">Could not load stats.</p>');
        }
    });

    $('#saveLinkChangesBtn').click(async function () {
        const isPublic = $('#linkVisibilitySwitch').prop('checked');
        const btn = this;
        addSpinnerToButton(btn);

        try {
            const resp = await fetch(API + 'Links/privacy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    linkId: selectedLink.LinkId,
                    isPrivate: !isPublic
                }),
            });
            if (!resp.ok) throw new Error('Failed to update visibility.');

            createPopup('Visibility updated!');
            linkModal.hide();
            // This is a placeholder for reloading the table data. You might need a more robust solution.
            location.reload();
        } catch (e) {
            console.error("Save visibility failed:", e);
            createPopupError('Could not save visibility.');
        } finally {
            restoreButton(btn);
        }
    });

    $('#changePasswordBtn').click(async function () {
        const currentPassword = $('#currentPassword').val();
        const newPassword = $('#newPassword').val();
        const btn = this;

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
            const resp = await fetch(API + 'Links/password', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    linkId: selectedLink.LinkId,
                    userId: currentUserID,
                    currentPassword: currentPassword,
                    newPassword: newPassword,
                }),
            });

            const result = await resp.json();

            if (!resp.ok) {
                throw new Error(result.message || 'An unknown error occurred.');
            }

            createPopup('Password changed successfully!');
            $('#currentPassword, #newPassword').val('');
            $('#revealedPasswordText').data('password', newPassword);

        } catch (e) {
            console.error("Password change failed:", e);
            $('#passwordUpdateError').text(e.message);
        } finally {
            restoreButton(btn);
        }
    });

    $('#forgotPasswordBtn').click(function () {
        const storedPassword = $('#revealedPasswordText').data('password');
        if (storedPassword) {
            $('#revealedPasswordText').text(storedPassword);
            $('#revealedPassword').slideDown();
        }
    });

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
            // Remove the row from the DataTable without a full reload for a smoother UX
            $('#linksTable').DataTable().row($(this).parents('tr')).remove().draw();
        } catch (e) {
            console.error('Delete failed:', e);
            createPopupError('Could not delete link.');
        } finally {
            restoreButton(btn);
        }
    });
}


function renderCountryStats(statsData) {
    const container = $('#countryStatsContainer');
    container.empty();

    if (!statsData || Object.keys(statsData).length === 0) {
        container.html('<p class="text-muted small m-0">No country-specific data available.</p>');
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
    const passwordModal = new bootstrap.Modal(document.getElementById('passwordAccessModal'));
    const passwordInput = $('#accessPasswordInput');
    const errorMsg = $('#passwordAccessError');
    const unlockBtn = $('#unlockLinkBtn');

    passwordInput.val('').removeClass('is-invalid');
    errorMsg.text('');
    passwordModal.show();

    unlockBtn.off('click').on('click', async function () {
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
                    linkId: linkData.LinkId,
                    password: password
                })
            });
            const result = await resp.json();

            if (result.accessGranted) {
                passwordModal.hide();
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
