$(document).ready(function () {
    const COUNTRIES = [
        "Afghanistan", "Albania", "Algeria", "Andorra", "Angola", "Antigua and Barbuda", "Argentina", "Armenia", "Australia", "Austria", "Azerbaijan",
        "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bhutan", "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi",
        "Cambodia", "Cameroon", "Canada", "Cape Verde (Cabo Verde)", "Central African Republic", "Chad", "Chile", "China", "Colombia", "Comoros", "Congo, Republic of the", "Congo, Democratic Republic of the", "Costa Rica", "Côte d'Ivoire", "Croatia", "Cuba", "Cyprus", "Czech Republic",
        "Denmark", "Djibouti", "Dominica", "Dominican Republic",
        "Ecuador", "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia",
        "Fiji", "Finland", "France",
        "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Greece", "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
        "Haiti", "Honduras", "Hungary",
        "Iceland", "India", "Indonesia", "Iran", "Iraq", "Ireland", "Israel", "Italy",
        "Jamaica", "Japan", "Jordan",
        "Kazakhstan", "Kenya", "Kiribati", "Kosovo", "Kuwait", "Kyrgyzstan",
        "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Luxembourg",
        "Madagascar", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Mauritania", "Mauritius", "Mexico", "Micronesia", "Moldova", "Monaco", "Mongolia", "Montenegro", "Morocco", "Mozambique", "Myanmar",
        "Namibia", "Nauru", "Nepal", "Netherlands", "New Zealand", "Nicaragua", "Niger", "Nigeria", "North Korea", "North Macedonia", "Norway",
        "Oman",
        "Pakistan", "Palau", "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines", "Poland", "Portugal",
        "Qatar",
        "Romania", "Russia", "Rwanda",
        "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", "Samoa", "San Marino", "São Tomé and Príncipe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands", "Somalia", "South Africa", "South Korea", "South Sudan", "Spain", "Sri Lanka", "Sudan", "Suriname", "Sweden", "Switzerland", "Syria",
        "Tajikistan", "Tanzania", "Thailand", "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Tuvalu",
        "Uganda", "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Uruguay", "Uzbekistan",
        "Vanuatu", "Vatican City", "Venezuela", "Vietnam",
        "Yemen",
        "Zambia", "Zimbabwe",
    ];

    const $country = $("#country");
    COUNTRIES.forEach((c) => {
        $country.append(`<option value="${c}">${c}</option>`);
    });

    const userID = localStorage.getItem("userID");
    if (!userID) {
        window.location.href = "index.html";
        return;
    }

    let currentPictureKey = null;
    const $form = $(".edit-profile-form");

    function getS3KeyFromUrl(url) {
        if (!url) return null;
        try {
            const urlObject = new URL(url);
            return urlObject.pathname.substring(1);
        } catch (e) {
            console.error("Could not parse S3 URL:", e);
            if (url.includes('.com/')) {
                return url.split('.com/')[1];
            }
            return null;
        }
    }

    async function loadProfile() {
        try {
            // MODIFIED: Using POST with a body instead of GET with a query string
            const resp = await fetch(API + 'users/byid', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ userId: userID })
            });
            const j = await resp.json();
            const data = typeof j.body === "string" ? JSON.parse(j.body) : j.body;

            $("#name").val(data.FullName || "");
            $("#country").val(data.Country || "");

            currentPictureKey = getS3KeyFromUrl(data.Picture);
            console.log("Current picture key:", currentPictureKey);
        } catch (e) {
            console.error("Failed to load profile:", e);
            createPopupError("Could not load your profile data.");
        }
    }

    $form.on("submit", async function (e) {
        e.preventDefault();
        e.stopPropagation();

        if (!this.checkValidity()) {
            $(this).addClass("was-validated");
            return;
        }

        const name = $("#name").val().trim();
        const country = $("#country").val();
        const photoFile = $("#photo")[0].files[0] || null;

        const btn = $(this).find('button[type="submit"]').get(0);
        addSpinnerToButton(btn);

        let newPhotoInfo = null;
        let updatePayload = {
            FullName: name,
            Country: country,
        };

        try {
            if (photoFile) {
                const presignedResponse = await fetch(API + "uploads/image/request", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ contentType: photoFile.type }),
                });
                if (!presignedResponse.ok) throw new Error("Could not get upload URL.");
                
                const { uploadUrl, key, finalUrl } = await presignedResponse.json();
                
                const s3UploadResponse = await fetch(uploadUrl, {
                    method: "PUT",
                    body: photoFile,
                    headers: { "Content-Type": photoFile.type },
                });
                if (!s3UploadResponse.ok) throw new Error("Photo upload to S3 failed.");

                updatePayload.Picture = finalUrl;
                newPhotoInfo = { key: key }; 
            }

            const profileUpdateResponse = await fetch(API + "Users/update", {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    userId: userID,
                    updateData: updatePayload,
                    oldPictureKey: photoFile ? currentPictureKey : null,
                }),
            });

            if (!profileUpdateResponse.ok) {
                throw new Error("Failed to update profile information.");
            }

            createPopup("Profile saved successfully!");
            setTimeout(() => goToProfile(), 1500);
        } catch (err) {
            console.error("Profile update process failed:", err);

            if (newPhotoInfo) {
                console.log("Rolling back: deleting newly uploaded image.");
                try {
                    await fetch(API + "uploads/image", {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ key: newPhotoInfo.key }),
                    });
                } catch (deleteErr) {
                    console.error("CRITICAL: Rollback failed. Orphaned file may exist in S3:", newPhotoInfo.key);
                }
            }
            createPopupError("Could not save profile. Please try again.");
        } finally {
            restoreButton(btn);
        }
    });

    loadProfile();
});
