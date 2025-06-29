$(document).ready(() => {
  const $form = $(".new-item-form");
  const currentUser = localStorage.getItem("UserId");
  const site = `https://shortly-rlt.s3.us-east-1.amazonaws.com`;

  // Failsafe: Redirect if not logged in
  if (!currentUser) {
    window.location.href = "index.html";
    return;
  }

  // --- Real-time Character Counters ---
  $("#linkName, #linkDescription").on("input", function () {
    const el = $(this);
    const maxLength = el.attr("maxlength");
    const currentLength = el.val().length;
    el.next(".d-flex").find(".counter").text(`${currentLength}/${maxLength}`);
  });

  // --- Password Toggle Logic ---
  $("#isPasswordProtected").on("change", function () {
    const $passwordGroup = $(".password-group");
    if ($(this).is(":checked")) {
      $passwordGroup.slideDown("fast");
    } else {
      $passwordGroup.slideUp("fast");
      $("#linkPassword").val("").removeClass("is-invalid");
    }
  });

  // --- Cancel Button Logic ---
  $(".cancel").on("click", function () {
    Swal.fire({
      title: "Are you sure?",
      text: "Any unsaved changes will be lost.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#d33",
      cancelButtonColor: "#6c757d",
      confirmButtonText: "Yes, discard changes",
    }).then((result) => {
      if (result.isConfirmed) {
        window.location.href = "index.html";
      }
    });
  });

  // --- Form Submission Logic ---
  $form.on("submit", async function (e) {
    e.preventDefault();

    // --- Validation ---
    let isValid = true;
    $(".is-invalid").removeClass("is-invalid"); // Clear previous errors

    const $originalUrl = $("#originalUrl");
    if (!$originalUrl[0].checkValidity() || !$originalUrl.val().trim()) {
      $originalUrl.addClass("is-invalid");
      isValid = false;
    }

    const $linkName = $("#linkName");
    if (!$linkName.val().trim()) {
      $linkName
        .addClass("is-invalid")
        .next(".d-flex")
        .find(".error-message")
        .text("A link name is required.");
      isValid = false;
    } else {
      $linkName.next(".d-flex").find(".error-message").text("");
    }

    const $passwordInput = $("#linkPassword");
    if (
      $("#isPasswordProtected").is(":checked") &&
      $passwordInput.val().length < 4
    ) {
      $passwordInput.addClass("is-invalid");
      isValid = false;
    }

    if (!isValid) return;

    // --- API Call ---
    const submitBtn = $(this).find("button[type=submit]")[0];
    addSpinnerToButton(submitBtn);

    const payload = {
      url: $originalUrl.val().trim(),
      name: $linkName.val().trim(),
      description: $("#linkDescription").val().trim(),
      isPrivate: $("#isPrivate").is(":checked"),
      isPasswordProtected: $("#isPasswordProtected").is(":checked"),
      password: $passwordInput.val(),
      userId: currentUser,
    };

    try {
      const resp = await fetch(API + "links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const errorData = await resp.json();
        throw new Error(errorData.error || "Failed to create link.");
      }

      const result = await resp.json();

      // Show a success message with the new short URL
      Swal.fire({
        icon: "success",
        title: "Link Created!",
        html: `Your new short link is ready:<br><a href="${
          site + "/main/redirect.html?code=" + result.code
        }" target="_blank">${
          site + "/main/redirect.html?code=" + result.code
        }</a>`,
        confirmButtonText: "Awesome!",
      }).then(() => {
        window.location.href = `index.html`;
      });
    } catch (err) {
      console.error(err);
      createPopupError(err.message || "An unexpected error occurred.");
      restoreButton(submitBtn);
    }
  });
});
