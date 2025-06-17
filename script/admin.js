// admin.js
$(document).ready(async function () {
    // --- Security Check (Optional but Recommended) ---
    // const isAdmin = localStorage.getItem("isAdmin") === "true";
    // if (!isAdmin) {
    //     window.location.href = "index.html";
    //     return;
    // }

    // --- Initialize Both Tables ---
    initializeUsersTable();
    initializeLinksTable();

    // --- Users Table Logic ---
    async function initializeUsersTable() {
        let users = [];
        try {
            // Assumes an endpoint that gets all users and their link stats
            const resp = await fetch(API + "Users/allWithStats", { method: 'POST' });
            if (!resp.ok) throw new Error("Failed to fetch users");
            const body = await resp.json();
            // The body itself should be the array of users
            users = Array.isArray(body) ? body : JSON.parse(body);
        } catch (e) {
            console.error("Failed loading users:", e);
            // Display an error in the table
            $('#usersTable tbody').html('<tr><td colspan="6" class="text-center text-danger">Could not load user data.</td></tr>');
            return;
        }

        $('#usersTable').DataTable({
            data: users,
            columns: [
                { data: 'Username' },
                { data: 'FullName' },
                { data: 'Country' },
                { 
                    data: 'DateJoined',
                    render: (date) => new Date(date).toLocaleDateString()
                },
                { 
                    data: 'TotalClicks',
                    // Default to 0 if the value is not present
                    render: (total) => total || 0
                },
                {
                    data: null,
                    orderable: false,
                    searchable: false,
                    render: (data, type, row) => {
                        // The 'checked' property is based on the user's IsActive status
                        const isChecked = row.IsActive;
                        return `
                            <div class="form-check form-switch d-flex justify-content-center">
                                <input class="form-check-input user-active-toggle" type="checkbox" role="switch" 
                                       data-userid="${row.UserId}" ${isChecked ? 'checked' : ''}>
                            </div>`;
                    }
                }
            ],
            // NEW: Add a class to rows to indicate they are clickable
            rowCallback: function(row, data) {
                $(row).addClass('clickable-row');
            },
            paging: true,
            searching: true,
            info: false,
            lengthChange: false,
            pageLength: 10,
            language: {
                search: "_INPUT_",
                searchPlaceholder: "Filter users..."
            }
        });
    }

    // --- Links Table Logic ---
    async function initializeLinksTable() {
        let links = [];
        try {
            const resp = await fetch(API + "Links/all", { method: 'POST' });
            if (!resp.ok) throw new Error("Failed to fetch links");
            const { body } = await resp.json();
            links = JSON.parse(body);
        } catch (e) {
            console.error("Failed loading links:", e);
             $('#linksTable tbody').html('<tr><td colspan="6" class="text-center text-danger">Could not load link data.</td></tr>');
            return;
        }

        $('#linksTable').DataTable({
            data: links,
            columns: [
                { data: "Name" },
                { data: "Description" },
                // This render function correctly creates a clickable link
                { data: "String", render: (url) => `<a href="${url}" target="_blank" title="Open link in new tab">${url}</a>` },
                { data: "IsPrivate", render: (v) => (v ? "Private" : "Public") },
                { data: "IsPasswordProtected", render: (v) => (v ? "Yes" : "No") },
                {
                    data: null,
                    orderable: false,
                    searchable: false,
                    render: (data, type, row) => `<button class="btn btn-danger btn-sm delete-btn" data-linkid="${row.LinkId}">Delete</button>`
                }
            ],
            paging: true, searching: true, info: false, lengthChange: false, pageLength: 10,
            language: { search: "_INPUT_", searchPlaceholder: "Filter links..." }
        });
    }

    // --- Event Handlers ---

    // NEW: Handler for navigating to a user's profile on row click
    $('#usersTable').on('click', 'tbody tr', function(e) {
        // Prevent action if the click was on the switch itself or its direct container
        if ($(e.target).is('input.user-active-toggle') || $(e.target).closest('.form-switch').length) {
            return;
        }
        const rowData = $('#usersTable').DataTable().row(this).data();
        if (rowData && rowData.UserId) {
            window.location.href = `profile.html?userID=${rowData.UserId}`;
        }
    });

    // Handler for toggling user active status
    $('#usersTable').on('change', '.user-active-toggle', async function() {
        const checkbox = $(this);
        const userId = checkbox.data('userid');
        const desiredState = checkbox.prop('checked');
        const actionText = desiredState ? "unban" : "ban";

        // Revert checkbox state optimistically
        checkbox.prop('checked', !desiredState);

        const result = await Swal.fire({
            title: `Are you sure?`,
            text: `Do you want to ${actionText} this user? Their access will be changed immediately.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: `Yes, ${actionText} them!`
        });

        if (result.isConfirmed) {
            try {
                const resp = await fetch(API + 'Users/toggle-activity', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId: userId })
                });
                if (!resp.ok) throw new Error("API request failed");
                
                // On success, set the checkbox to the desired state
                checkbox.prop('checked', desiredState);
                createPopup(`User has been ${actionText}ned.`);
            } catch (e) {
                console.error(`Failed to ${actionText} user:`, e);
                createPopupError(`Could not ${actionText} the user.`);
                // The checkbox remains in its original, reverted state on failure
            }
        }
    });

    // Handler for deleting links
    $('#linksTable').on('click', '.delete-btn', async function () {
        const btn = $(this);
        const linkId = btn.data('linkid');
        
        const isConfirmed = await Swal.fire({
            title: 'Delete this link?',
            text: "This action cannot be undone.",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Yes, delete it!'
        }).then(result => result.isConfirmed);

        if (isConfirmed) {
            try {
                await fetch(API + 'Links/delete', { 
                    method: "DELETE",
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ linkId: linkId })
                });
                // Find the table instance and remove the row
                $('#linksTable').DataTable().row(btn.closest('tr')).remove().draw();
                createPopup('Link deleted.');
            } catch (e) {
                console.error("Delete failed:", e);
                createPopupError("Could not delete the link.");
            }
        }
    });
});
