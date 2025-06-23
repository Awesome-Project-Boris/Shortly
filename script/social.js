// social.js - REFACTORED FOR CLIENT-SIDE HANDLING

$(document).ready(() => {
    const API_URL = API; // from global.js
    const container = $("#usersContainer");
    const pagination = $("#pagination");
    const searchIn = $("#userSearchInput");
    const searchBtn = $("#userSearchBtn");
    const useMock = Array.isArray(window.MOCK_USERS); // Keep mock as fallback
    const USERS_PER_PAGE = 10;

    let allUsers = []; // Stores the complete list of users from the server
    let displayedUsers = []; // Stores the currently filtered list of users

    let currentPage = 1;

    /**
     * Renders a specific page of users from the displayedUsers array and builds pagination controls.
     * @param {number} page - The page number to display.
     */
    function displayPage(page) {
        currentPage = page;
        pagination.empty(); // Clear old pagination

        const totalPages = Math.ceil(displayedUsers.length / USERS_PER_PAGE);

        if (totalPages === 0) {
            container.html(`<div class="user-card no-users">No users found</div>`);
            return;
        }

        // --- Pagination Window Logic (to show a limited number of page links) ---
        const maxShow = 5;
        let startPage, endPage;
        if (totalPages <= maxShow) {
            startPage = 1;
            endPage = totalPages;
        } else {
            const maxPagesBeforeCurrent = Math.floor(maxShow / 2);
            const maxPagesAfterCurrent = Math.ceil(maxShow / 2) - 1;
            if (currentPage <= maxPagesBeforeCurrent) {
                startPage = 1;
                endPage = maxShow;
            } else if (currentPage + maxPagesAfterCurrent >= totalPages) {
                startPage = totalPages - maxShow + 1;
                endPage = totalPages;
            } else {
                startPage = currentPage - maxPagesBeforeCurrent;
                endPage = currentPage + maxPagesAfterCurrent;
            }
        }

        // --- Render Pagination Buttons ---
        const prevDisabled = currentPage === 1 ? "disabled" : "";
        pagination.append(`<li class="page-item ${prevDisabled}"><a class="page-link" href="#">Prev</a></li>`);

        for (let i = startPage; i <= endPage; i++) {
            const activeClass = i === currentPage ? "active" : "";
            pagination.append(`<li class="page-item ${activeClass}"><a class="page-link" href="#">${i}</a></li>`);
        }

        const nextDisabled = currentPage === totalPages ? "disabled" : "";
        pagination.append(`<li class="page-item ${nextDisabled}"><a class="page-link" href="#">Next</a></li>`);

        // --- Slice and render the users for the current page ---
        const startIndex = (currentPage - 1) * USERS_PER_PAGE;
        const endIndex = startIndex + USERS_PER_PAGE;
        const pageUsers = displayedUsers.slice(startIndex, endIndex);

        renderUserCards(pageUsers);
    }

    /**
     * Renders the user card HTML into the container.
     * @param {Array} users - The array of user objects to render.
     */
    function renderUserCards(users) {
        container.empty();
        if (!users.length) {
            container.html(`<div class="user-card no-users">No users match your search.</div>`);
            return;
        }
        users.forEach((u) => {
            // Normalize field names from either API (PascalCase) or mock (camelCase)
            const userId = u.UserId || u.userID;
            const username = u.Username || u.username;
            const linkCount = u.Links ? u.Links.length : (u.linkCount || 0); // Handle Links as array or count
            const picUrl = u.Picture || u.picture || "https://placehold.co/80x80/007bff/FFFFFF?text=??"; // Default avatar

            const card = $(`
                <div class="user-card mb-2" data-userid="${userId}">
                    <div class="d-flex align-items-center">
                        <img src="${picUrl}" alt="${username}" class="rounded-circle" style="width: 80px; height: 80px; object-fit: cover;"/>
                        <span class="username ms-3 fs-5">${username}</span>
                    </div>
                    <span class="links-count text-muted">
                        Links: ${linkCount}
                    </span>
                </div>`);

            card.on("click", function () {
                window.location.href = `profile.html?userID=${$(this).data('userid')}`;
            });
            container.append(card);
        });
    }

    /**
     * Filters the 'allUsers' array based on the search input and re-renders the page.
     */
    function doSearch() {
        const query = searchIn.val().trim().toLowerCase();
        if (query) {
            displayedUsers = allUsers.filter(u =>
                (u.Username || u.username).toLowerCase().includes(query)
            );
        } else {
            displayedUsers = allUsers; // If search is empty, show all users
        }
        displayPage(1); // Reset to the first page of results
    }

    // --- Event Handlers ---
    searchBtn.on("click", doSearch);
    searchIn.on("keyup", doSearch); // Make search more responsive

    pagination.on("click", "a", function (e) {
        e.preventDefault();
        const targetPageText = $(this).text();
        const totalPages = Math.ceil(displayedUsers.length / USERS_PER_PAGE);
        let targetPage = currentPage;

        if (targetPageText === "Prev" && currentPage > 1) {
            targetPage--;
        } else if (targetPageText === "Next" && currentPage < totalPages) {
            targetPage++;
        } else if (!isNaN(parseInt(targetPageText))) {
            targetPage = parseInt(targetPageText);
        }

        if (targetPage !== currentPage) {
            displayPage(targetPage);
        }
    });

    // --- Initial Data Load ---
    async function init() {

        // if (useMock) {
        //     console.log("Using mock user data.");
        //     allUsers = window.MOCK_USERS;
        //     displayedUsers = allUsers;
        //     displayPage(1);
        //     return;
        // }
        console.log(API_URL)

        try {
            // Assumes you have a 'Users/all' endpoint that returns a complete list
            const res = await fetch(`${API_URL}/users/get_all_active_users`);  // VVV
            if (!res.ok) throw new Error(`API responded with status ${res.status}`);
            const body = await res.json();
            //console.log(body.users)

            // const users = JSON.parse(body.users);
            const users = body.users;
            console.log(users)
            // const users = JSON.parse(body);
            allUsers = users;
            displayedUsers = allUsers;

            displayPage(1);
        } catch (e) {
            console.error("Failed to load users from API:", e);
            container.html(`<div class="text-center text-danger py-3">Failed to load users. Please try again later.</div>`);
        }
    }

    init();
});
