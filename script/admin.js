// admin.js
// Assumes global.js defines `const API = '<your-api-base-url>';
$(document).ready(function () {
    initializeUsersTable();
});

let currentUserId = null;

async function initializeUsersTable() {
    try {
        const resp = await fetch(API + "/users/get-all-users-with-stats", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
        if (!resp.ok) throw new Error(resp.statusText);
        const { users } = await resp.json();

        // Destroy old table if exists
        if ($.fn.DataTable.isDataTable("#usersTable")) {
            $("#usersTable").DataTable().clear().destroy();
        }

        const usersTable = $("#usersTable").DataTable({
            data: users,
            columns: [
                { data: "userId", visible: false },
                { data: "userName", title: "User Name" },
                { data: "fullName", title: "Full Name" },
                { data: "country", title: "Country" },
                {
                    data: "dateJoined",
                    title: "Date Joined",
                    render: d => new Date(d).toLocaleDateString()
                },
                {
                    data: "totalClicks",
                    title: "Total Clicks",
                    render: t => t || 0
                },
                {
                    data: "active",
                    title: "Active",
                    render: a => `<input type=\"checkbox\" disabled ${a ? 'checked' : ''}/>`
                }
            ]
        });

        // Row click → load links
        $("#usersTable tbody").off("click").on("click", "tr", function () {
            const data = usersTable.row(this).data();
            currentUserId = data.userId;
            renderLinksTable(currentUserId);
        });
    } catch (e) {
        console.error("Error loading users:", e);
        createPopupError("Could not load users.");
    }
}

async function renderLinksTable(userId) {
    try {
        const resp = await fetch(API + "/users/get-all-users-with-stats", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ userId })
        });
        if (!resp.ok) throw new Error(resp.statusText);
        const { links } = await resp.json();

        // Destroy old table if exists
        if ($.fn.DataTable.isDataTable("#linksTable")) {
            $("#linksTable").DataTable().clear().destroy();
        }

        const linksTable = $("#linksTable").DataTable({
            data: links,
            columns: [
                { data: "linkId", visible: false },
                { data: "linkName", title: "Link Name" },
                { data: "description", title: "Description" },
                {
                    data: "link",
                    title: "Link",
                    render: url => `<a href=\"${url}\" target=\"_blank\">${url}</a>`
                },
                {
                    data: "publicPrivate",
                    title: "Public/Private",
                    render: p => p ? "Private" : "Public"
                },
                {
                    data: "hasPassword",
                    title: "Has Password",
                    render: h => h ? "Yes" : "No"
                },
                {
                    data: "active",
                    title: "Active",
                    render: a => a ? "Yes" : "No"
                },
                {
                    data: null,
                    title: "Action",
                    orderable: false,
                    render: (_, __, row) => {
                        return `<button class=\"toggle-btn\">${row.active ? 'Delete' : 'Restore'}</button>`;
                    }
                }
            ]
        });

        // Delete/Restore click
        $("#linksTable tbody").off("click").on("click", ".toggle-btn", async function () {
            const btn = $(this);
            const rowData = linksTable.row(btn.closest("tr")).data();
            const linkId = rowData.linkId;
            const endpoint = rowData.active ? "/links/delete" : "/links/restore";
            try {
                await fetch(API + endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ linkId })
                });
                createPopup(rowData.active ? "Link deleted." : "Link restored.");
                renderLinksTable(currentUserId);
            } catch (e) {
                console.error("Error toggling link:", e);
                createPopupError("Could not update link status.");
            }
        });
    } catch (e) {
        console.error("Error loading links:", e);
        createPopupError("Could not load links.");
    }
}
