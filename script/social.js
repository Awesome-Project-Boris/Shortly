// social.js
// runs after jQuery, Bootstrap & global.js

$(document).ready(() => {
  const API_URL = API; // from global.js
  const container = $("#usersContainer");
  const pagination = $("#pagination");
  const searchIn = $("#userSearchInput");
  const searchBtn = $("#userSearchBtn");

  let pagesData = {}; // cache per page
  let totalPages = 0;
  let currentPage = 1;
  let searchQuery = "";

  // Detect mock
  const useMock = Array.isArray(window.MOCK_USERS);

  // Fetch total pages (all vs. search)
  async function fetchCount() {
    if (useMock) {
      const arr = filterMock();
      totalPages = Math.ceil(arr.length / 10) || 1;
      return;
    }
    try {
      const url = searchQuery
        ? `${API_URL}Users/search/count?query=${encodeURIComponent(
            searchQuery
          )}`
        : `${API_URL}Users/count`;
      const res = await fetch(url);
      const { body } = await res.json();
      const count = JSON.parse(body).count ?? JSON.parse(body);
      totalPages = Math.ceil(count / 10) || 1;
    } catch (e) {
      console.error("Count error:", e);
      totalPages = 1;
    }
  }

  // Pagination window
  function getPagesWindow() {
    const maxShow = 5;
    if (totalPages <= maxShow) {
      return [...Array(totalPages)].map((_, i) => i + 1);
    }
    const half = Math.floor(maxShow / 2);
    let start = currentPage - half;
    let end = currentPage + half;
    if (start < 1) {
      start = 1;
      end = maxShow;
    }
    if (end > totalPages) {
      end = totalPages;
      start = totalPages - maxShow + 1;
    }
    return Array.from({ length: end - start + 1 }, (_, i) => start + i);
  }

  // Render pagination
  function renderPagination() {
    pagination.empty();
    const prevDisabled = currentPage === 1 ? "disabled" : "";
    const nextDisabled = currentPage === totalPages ? "disabled" : "";

    pagination.append(`
      <li class="page-item ${prevDisabled}">
        <a class="page-link" href="#">Prev</a>
      </li>`);

    getPagesWindow().forEach((p) =>
      pagination.append(`
        <li class="page-item ${p === currentPage ? "active" : ""}">
          <a class="page-link" href="#">${p}</a>
        </li>`)
    );

    pagination.append(`
      <li class="page-item ${nextDisabled}">
        <a class="page-link" href="#">Next</a>
      </li>`);
  }

  // Handle page clicks
  pagination.on("click", "a", (e) => {
    e.preventDefault();
    const txt = $(e.currentTarget).text();
    let tgt = currentPage;
    if (txt === "Prev" && currentPage > 1) tgt = currentPage - 1;
    else if (txt === "Next" && currentPage < totalPages) tgt = currentPage + 1;
    else if (!isNaN(+txt)) tgt = +txt;
    if (tgt !== currentPage) loadPage(tgt);
  });

  // Filter mock data
  function filterMock() {
    if (!useMock) return [];
    if (!searchQuery) return window.MOCK_USERS;
    return window.MOCK_USERS.filter((u) =>
      u.username.toLowerCase().includes(searchQuery)
    );
  }

  // Load & render a page
  async function loadPage(page) {
    currentPage = page;
    renderPagination();
    if (pagesData[page]) {
      return renderUsers(pagesData[page]);
    }

    // show spinner
    container.html(`
      <div class="loading-spinner text-center">
        <div class="spinner-border" role="status"></div>
      </div>`);

    if (useMock) {
      const arr = filterMock();
      const start = (page - 1) * 10;
      const users = arr.slice(start, start + 10);
      pagesData[page] = users;
      return renderUsers(users);
    }

    // real fetch
    try {
      const offset = (page - 1) * 10;
      const url = searchQuery
        ? `${API_URL}Users/search?query=${encodeURIComponent(
            searchQuery
          )}&offset=${offset}&limit=10`
        : `${API_URL}Users/all?offset=${offset}&limit=10`;
      const res = await fetch(url);
      const { body } = await res.json();
      const users = JSON.parse(body);
      pagesData[page] = users;
      renderUsers(users);
    } catch (e) {
      console.error("Load error:", e);
      container.html(`
        <div class="text-center text-danger py-3">
          Failed to load users.
        </div>`);
    }
  }

  // Render user cards
  function renderUsers(users) {
    if (!users.length) {
      container.html(`
        <div class="user-card no-users">
          No users found
        </div>`);
      return;
    }
    container.empty();
    users.forEach((u) => {
      const picUrl = u.picture || "";
      const card = $(`
        <div class="user-card mb-2">
          <div class="d-flex align-items-center">
            <img src="${picUrl}" alt="${u.username}" />
            <span class="username ms-3">${u.username}</span>
          </div>
          <span class="links-count">
            Links available: ${u.linkCount}
          </span>
        </div>`);
      card.on(
        "click",
        () => (window.location.href = `profile.html?userID=${u.userID}`)
      );
      container.append(card);
    });
  }

  // Search handlers
  function doSearch() {
    searchQuery = searchIn.val().trim().toLowerCase();
    pagesData = {};
    currentPage = 1;
    fetchCount()
      .then(() => renderPagination())
      .then(() => loadPage(1));
  }
  searchBtn.on("click", doSearch);
  searchIn.on("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      doSearch();
    }
  });

  // Init
  (async () => {
    await fetchCount();
    renderPagination();
    loadPage(1);
  })();
});
