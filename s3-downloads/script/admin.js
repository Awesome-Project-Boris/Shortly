// admin.js
// Assumes global.js defines `const API = '<your-api-base-url>';
// Cache selectors
const $usersSpinner = $("#usersSpinner");
const $linksSpinner = $("#linksSpinner");

$(document).ready(() => initializeUsersTable());
let currentUserId = null;

async function initializeUsersTable() {
    try {
        // Show spinner inside footer cell
        $usersSpinner.show();

        const resp = await fetch(API + "/users/get-all-users-with-stats", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
        if (!resp.ok) throw new Error(resp.statusText);
        const { users } = await resp.json();

        const $table = $("#usersTable");
        // Reset DataTable
        if ($.fn.DataTable.isDataTable($table)) {
            $table.DataTable().clear().destroy();
        }

        // Initialize DataTable
        $table.DataTable({
            data: users,
            rowId: "userId",
            columns: [
                { data: "userName" },
                { data: "fullName" },
                { data: "country" },
                { data: "dateJoined", render: d => new Date(d).toLocaleDateString() },
                { data: "totalClicks", render: t => t || 0 },
                { data: "active", render: a => `<input type=\"checkbox\" disabled ${a ? 'checked' : ''}/>` }
            ],
            // Hide spinner once table draw is complete
            drawCallback: () => $usersSpinner.hide()
        })
            .off("click").on("click", "tbody tr", function () {
                currentUserId = this.id;
                renderLinksTable(currentUserId);
            });
    } catch (e) {
        console.error("Error loading users:", e);
        createPopupError("Could not load users.");
        $usersSpinner.hide();
    }
}

async function renderLinksTable(userId) {
    try {
        $linksSpinner.show();

        const resp = await fetch(API + "/users/get-all-users-with-stats", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ userId })
        });
        if (!resp.ok) throw new Error(resp.statusText);
        const { links } = await resp.json();

        const $table = $("#linksTable");
        if ($.fn.DataTable.isDataTable($table)) {
            $table.DataTable().clear().destroy();
        }

        $table.DataTable({
            data: links,
            rowId: "linkId",
            columns: [
                { data: "linkName" },
                { data: "description" },
                { data: "link", render: url => `<a href=\"${url}\" target=\"_blank\">${url}</a>` },
                { data: "publicPrivate", render: p => p ? "Private" : "Public" },
                { data: "hasPassword", render: h => h ? "Yes" : "No" },
                { data: "active", render: a => a ? "Yes" : "No" },
                {
                    data: null, orderable: false,
                    render: (_, __, r) => `<button class=\"toggle-btn\">${r.active ? 'Delete' : 'Restore'}</button>`
                }
            ],
            drawCallback: () => $linksSpinner.hide()
        })
            .off("click").on("click", "tbody .toggle-btn", async function () {
                const rowData = $(this).closest('tr').data();
                const endpoint = rowData.active ? "/links/delete" : "/links/restore";
                try {
                    await fetch(API + endpoint, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ linkId: rowData.linkId })
                    });
                    createPopup(rowData.active ? "Link deleted." : "Link restored.");
                    renderLinksTable(currentUserId);
                } catch (err) {
                    console.error("Error toggling link:", err);
                    createPopupError("Could not update link status.");
                    $linksSpinner.hide();
                }
            });
    } catch (e) {
        console.error("Error loading links:", e);
        createPopupError("Could not load links.");
        $linksSpinner.hide();
    }
}