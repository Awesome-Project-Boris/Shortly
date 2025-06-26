$(document).ready(function () {
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

  const userID = localStorage.getItem("UserId");
  if (!userID) {
    // Redirect if no user is logged in
    // window.location.href = "index.html";
    console.error("User ID not found in localStorage.");
    createPopupError("You must be logged in to edit a profile.");
    return;
  }

  // --- State Variables ---
  let newPictureUrl = null; // To store the URL of a newly uploaded picture
  const $form = $(".edit-profile-form");
  const $imagePreview = $("#profileImagePreview");
  const $imageSpinner = $("#imageSpinner");
  let defaultPictureUrl =
    window.location.origin + "/media/profile-photos/default-user.png";

  // --- Function to Load User Profile ---
  async function loadProfile() {
    try {
      const resp = await fetch(API + "users/get-user-by-id", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ProfileOwnerId: userID,
          LoggedInUserId: userID,
        }),
      });
      if (!resp.ok) throw new Error("Failed to load profile");

      const data = await resp.json();
      const userInfo = data.userInfo;

      if (userInfo) {
        $("#name").val(userInfo.FullName || "");
        $("#country").val(userInfo.Country || "");
        $imagePreview.attr("src", userInfo.Picture || defaultPictureUrl);
      }
    } catch (e) {
      console.error("Failed to load profile:", e);
      createPopupError("Could not load your profile data.");
    }
  }

  // --- Event Handler for Image Upload ---
  async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    $imageSpinner.css("display", "flex");

    try {
      // 1. Get a presigned URL from our backend
      const presignedResponse = await fetch(
        API + "images/request_image_upload_url",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ contentType: file.type }),
        }
      );
      if (!presignedResponse.ok) throw new Error("Could not get upload URL.");

      const { uploadUrl, finalUrl } = await presignedResponse.json();

      // 2. Upload the file directly to S3 using the presigned URL
      const s3UploadResponse = await fetch(uploadUrl, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });
      if (!s3UploadResponse.ok) throw new Error("Photo upload to S3 failed.");

      // 3. Update the UI and state
      $imagePreview.attr("src", URL.createObjectURL(file));
      newPictureUrl = finalUrl; // Store the final URL for saving
      createPopup('Image updated! Click "Apply Changes" to save.');
    } catch (err) {
      console.error("Image upload failed:", err);
      createPopupError("Image upload failed. Please try again.");
    } finally {
      $imageSpinner.css("display", "none");
    }
  }

  $("#photo").on("change", handleImageUpload);
  $imagePreview.on("click", () => $("#photo").click()); // Allow clicking image to open file dialog

  // --- Event Handler for Removing Picture ---
  $("#removePictureBtn").on("click", async function () {
    const btn = this;
    addSpinnerToButton(btn);
    try {
      const response = await fetch(API + "users/delete-image", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userId: userID, pictureUrl: defaultPictureUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || "Failed to remove picture.");
      }

      createPopup("Picture removed successfully!");
      $imagePreview.attr("src", defaultPictureUrl); // Update the UI
      newPictureUrl = defaultPictureUrl; // Set the URL to be saved if other fields are updated
    } catch (err) {
      console.error("Failed to remove picture:", err);
      createPopupError(err.message || "Could not remove picture.");
    } finally {
      restoreButton(btn);
    }
  });

  // --- Event Handler for Form Submission ---
  $form.on("submit", async function (e) {
    e.preventDefault();
    e.stopPropagation();

    if (!this.checkValidity()) {
      $(this).addClass("was-validated");
      return;
    }

    const btn = $(this).find('button[type="submit"]').get(0);
    addSpinnerToButton(btn);

    // Build the payload with all fields that might be updated
    const updatePayload = {
      userId: userID,
      FullName: $("#name").val().trim(),
      Country: $("#country").val(),
    };

    // Only add the 'Picture' field if a new one was uploaded or it was removed
    if (newPictureUrl) {
      updatePayload.Picture = newPictureUrl;
    }

    try {
      const profileUpdateResponse = await fetch(API + "users", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatePayload),
      });

      if (!profileUpdateResponse.ok) {
        const errorData = await profileUpdateResponse.json();
        throw new Error(errorData.message || "Failed to update profile.");
      }

      createPopup("Profile saved successfully!");
      // Redirect to the profile page after a short delay
      setTimeout(
        () => (window.location.href = `profile.html?userID=${userID}`),
        1500
      );
    } catch (err) {
      console.error("Profile update failed:", err);
      // NOTE: Rollback logic for S3 has been removed as per the requirements.
      createPopupError(err.message || "Could not save profile.");
    } finally {
      restoreButton(btn);
    }
  });

  $("#cancelBtn").on("click", function () {
    window.location.href = `profile.html?userID=${userID}`;
  });

  // --- Initial Load ---
  loadProfile();
});
