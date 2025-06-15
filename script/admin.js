// admin.js
// runs after jQuery, DataTables & Bootstrap have loaded (all deferred)

$(document).ready(async function () {

  const me = localStorage.getItem("userID");     // FOR ADMIN ONLY ACCESS
  // try {
  //   const resp = await fetch(API + `Users/isadmin?userID=${me}`);
  //   const { body } = await resp.json();
  //   if (!JSON.parse(body).isAdmin) {
  //     window.location.href = "index.html";
  //     return;
  //   }
  // } catch {
  //   window.location.href = "index.html";
  //   return;
  // }

  // Fetch all links
  let links = [];
  try {
    const resp = await fetch(API + "Links/all");
    const { body } = await resp.json();
    links = JSON.parse(body);
  } catch (e) {
    console.error("Failed loading links:", e);
  }

  // Populate DataTable
  const table = $("#linksTable").DataTable({
    data: links,
    columns: [
      { data: "name" },
      { data: "description" },
      {
        data: "shortUrl",
        render: (url) => `<a href="${url}" target="_blank">${url}</a>`,
      },
      {
        data: "isPublic",
        render: (v) => (v ? "Public" : "Private"),
      },
      {
        data: "hasPassword",
        render: (v) => (v ? "Yes" : "No"),
      },
      {
        data: null,
        orderable: false,
        searchable: false,
        render: (_, __, row) =>
          `<button class="btn btn-danger btn-sm delete-btn" data-id="${row.linkID}">Delete</button>`,
      },
    ],
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

  //  Handle delete clicks
  $("#linksTable tbody").on("click", ".delete-btn", async function () {
    const $btn = $(this);
    const id = $btn.data("id");
    if (!confirm("Are you sure you want to delete this link?")) return;

    try {
      await fetch(API + `Links/delete?linkID=${id}`, { method: "DELETE" });
      table.row($btn.closest("tr")).remove().draw();
    } catch (e) {
      console.error("Delete failed:", e);
      alert("Could not delete link.");
    }
  });
});
