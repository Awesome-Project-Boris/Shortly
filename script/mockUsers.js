// mockUsers.js

// —————————————————————————
// 30 Fake users for the “Find Users” page
// —————————————————————————
window.MOCK_USERS = Array.from({ length: 30 }, (_, i) => ({
  userID: `user${1000 + i}`,
  username: `MockUser${i + 1}`,
  linkCount: Math.floor(Math.random() * 20),
  picture: `https://i.pravatar.cc/100?img=${i + 1}`,
}));

// —————————————————————————
// Fake pending friend‐requests for the offcanvas
// —————————————————————————
window.MOCK_FRIEND_REQUESTS = [
  {
    notificationID: "req1",
    userID: "u101",
    username: "Alice",
    picture: "https://i.pravatar.cc/30?img=5",
  },
  {
    notificationID: "req2",
    userID: "u102",
    username: "Bob",
    picture: "https://i.pravatar.cc/30?img=15",
  },
];

// —————————————————————————
// Fake friends list for the offcanvas
// —————————————————————————
window.MOCK_FRIENDS = [
  {
    userID: "u201",
    username: "Carol",
    picture: "https://i.pravatar.cc/30?img=25",
  },
  {
    userID: "u202",
    username: "Dave",
    picture: "https://i.pravatar.cc/30?img=35",
  },
  {
    userID: "u203",
    username: "Eve",
    picture: "https://i.pravatar.cc/30?img=45",
  },
];
