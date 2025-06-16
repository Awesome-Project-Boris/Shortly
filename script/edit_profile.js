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
  // if (!userID) return (location.href = "index.html");

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

    } catch (e) {
      console.error("Failed to load profile:", e);
    }
  }

  loadProfile();

  // In Shortly/script/edit_profile.js

$(".edit-profile-form").on("submit", async function (e) {
  e.preventDefault();
  e.stopPropagation();

  const form = this;
  // First, perform standard browser validation
  if (!form.checkValidity()) {
    $(form).addClass("was-validated");
    return;
  }

  const name = $("#name").val().trim();
  const country = $("#country").val();
  const photoEl = $("#photo")[0];
  const photoFile = photoEl.files[0] || null;

  const btn = $(form).find('button[type="submit"]').get(0);
  addSpinnerToButton(btn);

  let uploadedPhotoInfo = null; // Will store { url, key } after a successful upload

  try {
    // STEP 1: UPLOAD PHOTO (only if a new one is selected)
    if (photoFile) {
      console.log("New photo selected. Requesting upload URL...");
      // 1a: Get a pre-signed URL from your new API endpoint
      const presignedResponse = await fetch(API + "uploads/image/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Send the file type to the backend so it can be set correctly in S3
        body: JSON.stringify({ contentType: photoFile.type })
      });

      if (!presignedResponse.ok) {
        throw new Error("Could not get an upload URL from the server.");
      }
      
      // The backend returns the URL to upload to, the final URL, and the file key
      const { uploadUrl, key, finalUrl } = await presignedResponse.json();
      
      // 1b: Upload the file directly to S3 using the secure pre-signed URL
      console.log("Uploading photo directly to S3...");
      const s3UploadResponse = await fetch(uploadUrl, {
        method: "PUT",
        body: photoFile,
        headers: { "Content-Type": photoFile.type }
      });

      if (!s3UploadResponse.ok) {
        throw new Error("Failed to upload photo file to S3.");
      }
      
      console.log("Photo uploaded successfully.");
      // Store the new photo's URL and key for the next step
      uploadedPhotoInfo = { url: finalUrl, key: key };
    }

    // STEP 2: UPDATE USER PROFILE IN DYNAMODB
    console.log("Updating user profile...");
    const userUpdatePayload = {
      userID: userID,
      name: name,
      country: country,
    };

    // Only add the 'picture' field to the payload if a new photo was uploaded
    if (uploadedPhotoInfo) {
      userUpdatePayload.picture = uploadedPhotoInfo.url;
    }

    const userUpdateResponse = await fetch(API + "Users/update", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userUpdatePayload),
    });

    if (!userUpdateResponse.ok) {
      // If this step fails, the 'catch' block below will trigger the rollback
      throw new Error("Failed to update user profile in the database.");
    }

    createPopup("Profile saved successfully!");
    goToProfile();

  } catch (err) {
    console.error("An error occurred during the profile update process:", err);

    // STEP 3: ROLLBACK! Delete the image from S3 if it was uploaded but the profile update failed.
    if (uploadedPhotoInfo) {
      console.log("Profile update failed. Starting rollback to delete orphaned image...");
      try {
        await fetch(API + "uploads/image", {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: uploadedPhotoInfo.key }) // Send the key of the file to delete
        });
        console.log("Orphaned image successfully deleted from S3.");
      } catch (deleteErr) {
        // This is a critical error, as you now have an orphaned file.
        // You may want to log this to a monitoring service.
        console.error("CRITICAL: Failed to delete orphaned image during rollback.", deleteErr);
      }
    }

    createPopupError("Could not save profile. Please try again.");

  } finally {
    // This runs whether the process succeeded or failed
    restoreButton(btn);
  }
});
});
