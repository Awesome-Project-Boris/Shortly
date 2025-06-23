$(document).ready(() => {
    const $form = $(".new-item-form");
    // const $name = $("#linkName"); // REMOVED: This element does not exist in the HTML
    const $desc = $("#description");
    const $url = $("#url");
    const $isPublic = $("#isPublic");
    const $pwdSwitch = $("#passwordProtected");
    const $pwdGroup = $(".password-group");
    const $pwd = $("#password");
    const currentUser = localStorage.getItem("userID");

    // MODIFIED: Removed the non-existent 'name' field from the validation array
    const fields = [
        {
            $el: $desc,
            validate: (val) => val.length <= 100,
            max: 100,
            msg: "Max 100 chars.",
        },
        {
            $el: $url,
            validate: (val) => /^\S{1,32}$/.test(val.trim()), // Validate the trimmed value
            max: 32,
            msg: "Required. 1-32 chars, no spaces.",
        },
    ];
    const pwdField = {
        $el: $pwd,
        validate: (val) => val.length >= 4,
        max: 50,
        msg: "Required. Min 4 chars.",
    };

    function markValid($el) {
        $el.addClass("is-valid").removeClass("is-invalid");
    }

    function markInvalid($el, message) {
        $el.addClass("is-invalid").removeClass("is-valid");
        $el.closest(".mb-3").find(".error-message").text(message);
    }

    function clearState($el) {
        $el.removeClass("is-valid is-invalid");
        $el.closest(".mb-3").find(".error-message").text("");
    }

    function setupRealtimeValidation({ $el, validate, max, msg }) {
        if (!$el.length) return; // Failsafe if an element doesn't exist
        const $cnt = $el.closest(".mb-3").find(".counter").text(`0/${max}`);
        $el.on("input", () => {
            const val = $el.val();
            const len = val.length;
            $cnt.text(`${len}/${max}`).toggleClass("exceeded", len > max);
            
            clearState($el);
            // Description is optional, so we don't validate it if empty
            if ($el.is($desc) && !val) return; 

            if (len > max || !validate(val)) {
                markInvalid($el, msg);
            } else {
                markValid($el);
            }
        });
    }

    fields.forEach(setupRealtimeValidation);
    setupRealtimeValidation(pwdField);

    // Password toggle
    $pwdGroup.hide();
    $pwdSwitch.on("change", () => {
        clearState($pwd);
        if ($pwdSwitch.is(":checked")) {
            $pwdGroup.slideDown("fast");
        } else {
            $pwdGroup.slideUp("fast");
            $pwd.val(''); // Clear the password field when hiding
        }
    });

    // Form submission
    $form.on("submit", async (e) => {
        e.preventDefault();

        let isFormValid = true;

        // --- NEW: More robust validation on submit ---
        
        // Validate URL (Link Identifier)
        const urlValue = $url.val().trim();
        if (!/^\S{1,32}$/.test(urlValue)) {
            markInvalid($url, "Required. 1-32 chars, no spaces.");
            isFormValid = false;
        }

        // Validate Password if required
        const isPasswordProtected = $pwdSwitch.is(":checked");
        const passwordValue = $pwd.val();
        if (isPasswordProtected && passwordValue.length < 4) {
            markInvalid($pwd, "Required. Min 4 chars.");
            isFormValid = false;
        }

        if (!isFormValid) {
            // Focus the first invalid field for better UX
            $('.is-invalid').first().focus();
            return; 
        }

        const submitBtn = $form.find("button[type=submit]")[0];
        addSpinnerToButton(submitBtn);

        // Build payload, REMOVED 'name' field
        const payload = {
            description: $desc.val().trim(),
            shortUrl: urlValue,
            isPublic: $isPublic.is(":checked"),
            isPasswordProtected: isPasswordProtected,
            userId: currentUser // Make sure to send the user ID
        };
        if (isPasswordProtected) {
            payload.password = passwordValue;
        }

        try {
            // Note: The Lambda expects 'userId' and 'shortUrl'. Let's ensure our payload matches.
            // Your Lambda from before might expect 'url' instead of 'shortUrl' for the identifier. Adjust if needed.
            const resp = await fetch(API + "links", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            if (!resp.ok) {
                 const errorData = await resp.json();
                 throw new Error(errorData.error || "Request failed");
            }

            createPopup("Link added successfully!");
            setTimeout(() => {
                window.location.href = `profile.html?userID=${currentUser}`;
            }, 1200);
        } catch (err) {
            console.error(err);
            createPopupError(err.message || "Failed to add link.");
            restoreButton(submitBtn);
        }
    });
});
