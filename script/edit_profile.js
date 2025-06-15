// edit_profile.js
// runs after jQuery & global.js

console.log(
  "✅ edit_profile.js loaded, country select length:",
  $("#country").length
);

$(document).ready(function () {
  // Build navbar from global.js
  // buildNavBar();

  const userID = localStorage.getItem("userID");
  if (!userID) return (location.href = "index.html");

  const COUNTRIES = [
    "Afghanistan",
    "Albania",
    "Algeria",
    "Andorra",
    "Angola",
    "Antigua and Barbuda",
    "Argentina",
    "Armenia",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahamas",
    "Bahrain",
    "Bangladesh",
    "Barbados",
    "Belarus",
    "Belgium",
    "Belize",
    "Benin",
    "Bhutan",
    "Bolivia",
    "Bosnia and Herzegovina",
    "Botswana",
    "Brazil",
    "Brunei",
    "Bulgaria",
    "Burkina Faso",
    "Burundi",
    "Cambodia",
    "Cameroon",
    "Canada",
    "Cape Verde (Cabo Verde)",
    "Central African Republic",
    "Chad",
    "Chile",
    "China",
    "Colombia",
    "Comoros",
    "Congo, Republic of the",
    "Congo, Democratic Republic of the",
    "Costa Rica",
    "Côte d'Ivoire",
    "Croatia",
    "Cuba",
    "Cyprus",
    "Czech Republic",
    "Denmark",
    "Djibouti",
    "Dominica",
    "Dominican Republic",
    "Ecuador",
    "Egypt",
    "El Salvador",
    "Equatorial Guinea",
    "Eritrea",
    "Estonia",
    "Eswatini",
    "Ethiopia",
    "Fiji",
    "Finland",
    "France",
    "Gabon",
    "Gambia",
    "Georgia",
    "Germany",
    "Ghana",
    "Greece",
    "Grenada",
    "Guatemala",
    "Guinea",
    "Guinea-Bissau",
    "Guyana",
    "Haiti",
    "Honduras",
    "Hungary",
    "Iceland",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Jamaica",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kiribati",
    "Kosovo",
    "Kuwait",
    "Kyrgyzstan",
    "Laos",
    "Latvia",
    "Lebanon",
    "Lesotho",
    "Liberia",
    "Libya",
    "Liechtenstein",
    "Lithuania",
    "Luxembourg",
    "Madagascar",
    "Malawi",
    "Malaysia",
    "Maldives",
    "Mali",
    "Malta",
    "Marshall Islands",
    "Mauritania",
    "Mauritius",
    "Mexico",
    "Micronesia",
    "Moldova",
    "Monaco",
    "Mongolia",
    "Montenegro",
    "Morocco",
    "Mozambique",
    "Myanmar",
    "Namibia",
    "Nauru",
    "Nepal",
    "Netherlands",
    "New Zealand",
    "Nicaragua",
    "Niger",
    "Nigeria",
    "North Korea",
    "North Macedonia",
    "Norway",
    "Oman",
    "Pakistan",
    "Palau",
    "Panama",
    "Papua New Guinea",
    "Paraguay",
    "Peru",
    "Philippines",
    "Poland",
    "Portugal",
    "Qatar",
    "Romania",
    "Russia",
    "Rwanda",
    "Saint Kitts and Nevis",
    "Saint Lucia",
    "Saint Vincent and the Grenadines",
    "Samoa",
    "San Marino",
    "São Tomé and Príncipe",
    "Saudi Arabia",
    "Senegal",
    "Serbia",
    "Seychelles",
    "Sierra Leone",
    "Singapore",
    "Slovakia",
    "Slovenia",
    "Solomon Islands",
    "Somalia",
    "South Africa",
    "South Korea",
    "South Sudan",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Suriname",
    "Sweden",
    "Switzerland",
    "Syria",
    "Tajikistan",
    "Tanzania",
    "Thailand",
    "Timor-Leste",
    "Togo",
    "Tonga",
    "Trinidad and Tobago",
    "Tunisia",
    "Turkey",
    "Turkmenistan",
    "Tuvalu",
    "Uganda",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Vanuatu",
    "Vatican City",
    "Venezuela",
    "Vietnam",
    "Yemen",
    "Zambia",
    "Zimbabwe",
  ];

  const $country = $("#country");
  COUNTRIES.forEach((c) => {
    $country.append(`<option value="${c}">${c}</option>`);
  });

  // Fetch existing profile
  async function loadProfile() {
    try {
      const resp = await fetch(API + `Users/byid?userID=${userID}`);
      const j = await resp.json();
      const data = typeof j.body === "string" ? JSON.parse(j.body) : j.body;

      $("#name").val(data.name || "");
      $country.val(data.country || "");
      $("#phone").val(data.phone_number || "");

    } catch (e) {
      console.error("Failed to load profile:", e);
    }
  }

  loadProfile();

  $(".edit-profile-form").on("submit", async function (e) {
    e.preventDefault();
    e.stopPropagation();

    const form = this;
    if (!form.checkValidity()) {
      $(form).addClass("was-validated");
      return;
    }


    const name = $("#name").val().trim();
    const country = $("#country").val();
    const phone = $("#phone").val().trim();
    const photoEl = $("#photo")[0];
    const photoFile = photoEl.files[0] || null;


    const btn = $(form).find('button[type="submit"]').get(0);
    addSpinnerToButton(btn);

    try {
      let photoUrl = null;
      if (photoFile) {
        // e.g. upload to S3, get back URL — YOUR logic
        // photoUrl = await uploadPhoto(photoFile);
      }

      // PUT to API
      await fetch(API + "Users/update", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userID: userID,
          name: name,
          country: country,
          phoneNumber: phone,
          picture: photoUrl, 
        }),
      });

      createPopup("Profile saved!");
      goToProfile();
    } catch (err) {
      console.error("Save failed:", err);
      createPopupError("Could not save profile.");
    } finally {
      restoreButton(btn);
    }
  });
});
