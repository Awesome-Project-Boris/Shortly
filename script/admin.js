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

        const $table = $("#usersTable");
        // Reset table structure
        if ($.fn.DataTable.isDataTable($table)) {
            $table.DataTable().clear().destroy();
        }
        // Build table with thead and empty tbody
        const usersThead = `<thead><tr>
            <th>User Name</th>
            <th>Full Name</th>
            <th>Country</th>
            <th>Date Joined</th>
            <th>Total Clicks</th>
            <th>Active</th>
        </tr></thead>`;
        $table.html(usersThead + "<tbody></tbody>");

        const usersTable = $table.DataTable({
            data: users,
            rowId: "userId",
            columns: [
                { data: "userName" },
                { data: "fullName" },
                { data: "country" },
                {
                    data: "dateJoined",
                    render: d => new Date(d).toLocaleDateString()
                },
                {
                    data: "totalClicks",
                    render: t => t || 0
                },
                {
                    data: "active",
                    render: a => `<input type=\"checkbox\" disabled ${a ? 'checked' : ''}/>`
                }
            ]
        });

        // Row click → load links
        $table.off("click").on("click", "tbody tr", function () {
            currentUserId = this.id;
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

        const $table = $("#linksTable");
        // Reset table structure
        if ($.fn.DataTable.isDataTable($table)) {
            $table.DataTable().clear().destroy();
        }
        // Build table with thead and empty tbody
        const linksThead = `<thead><tr>
            <th>Link Name</th>
            <th>Description</th>
            <th>Link</th>
            <th>Public/Private</th>
            <th>Has Password</th>
            <th>Active</th>
            <th>Action</th>
        </tr></thead>`;
        $table.html(linksThead + "<tbody></tbody>");

        const linksTable = $table.DataTable({
            data: links,
            rowId: "linkId",
            columns: [
                { data: "linkName" },
                { data: "description" },
                {
                    data: "link",
                    render: url => `<a href=\"${url}\" target=\"_blank\">${url}</a>`
                },
                {
                    data: "publicPrivate",
                    render: p => p ? "Private" : "Public"
                },
                {
                    data: "hasPassword",
                    render: h => h ? "Yes" : "No"
                },
                {
                    data: "active",
                    render: a => a ? "Yes" : "No"
                },
                {
                    data: null,
                    orderable: false,
                    render: (_, __, row) => `<button class=\"toggle-btn\">${row.active ? 'Delete' : 'Restore'}</button>`
                }
            ]
        });

        // Action button click
        $table.off("click").on("click", "tbody .toggle-btn", async function () {
            const btn = $(this);
            const rowData = linksTable.row(btn.closest("tr")).data();
            const endpoint = rowData.active ? "/links/delete" : "/links/restore";
            try {
                await fetch(API + endpoint, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ linkId: rowData.linkId })
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
