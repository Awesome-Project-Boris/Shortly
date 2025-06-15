$(document).ready(() => {
  const $form = $(".new-item-form");
  const $name = $("#linkName");
  const $desc = $("#description");
  const $url = $("#url");
  const $public = $("#isPublic");
  const $pwdSwitch = $("#passwordProtected");
  const $pwdGroup = $(".password-group");
  const $pwd = $("#password");
  const currentUser = localStorage.getItem("userID");

  const fields = [
    {
      $el: $name,
      validate: (val) => !!val.trim(),
      max: 50,
      msg: "Required, max 50 chars.",
    },
    {
      $el: $desc,
      validate: (val) => val.length <= 100,
      max: 100,
      msg: "Max 100 chars.",
    },
    {
      $el: $url,
      // 1–32 non-space characters
      validate: (val) => /^\S{1,32}$/.test(val),
      max: 32,
      msg: "1-32 chars, no spaces.",
    },
  ];
  const pwdField = {
    $el: $pwd,
    validate: (val) => val.length >= 4,
    max: 50,
    msg: "Min 4 chars.",
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

  function setupRealtime({ $el, validate, max, msg }) {
    const $cnt = $el.closest(".mb-3").find(".counter").text(`0/${max}`);
    $el.on("input", () => {
      const val = $el.val();
      const len = val.length;
      $cnt.text(`${len}/${max}`).toggleClass("exceeded", len > max);

      clearState($el);
      if (!val && $el.is($desc)) return; // allow description empty
      if (len > max || !validate(val)) {
        markInvalid($el, msg);
      } else {
        markValid($el);
      }
    });
  }

  fields.forEach(setupRealtime);
  setupRealtime(pwdField);

  // Password toggle
  $pwdGroup.hide();
  $pwdSwitch.on("change", () => {
    clearState($pwd);
    if ($pwdSwitch.is(":checked")) {
      $pwdGroup.slideDown("fast");
    } else {
      $pwdGroup.slideUp("fast");
    }
  });

  // Form submission
  $form.on("submit", async (e) => {
    e.preventDefault();

    // Clear all states
    fields.forEach((f) => clearState(f.$el));
    clearState($pwd);

    const name = $name.val().trim();
    const desc = $desc.val().trim();
    const url = $url.val().trim();
    const isPublic = $public.is(":checked");
    const pwdProt = $pwdSwitch.is(":checked");
    const pwd = $pwd.val().trim();

    // Final validation
    for (let f of fields) {
      const val = f.$el.val();
      // allow description empty:
      if (f.$el.is($desc) && !val) continue;
      if (!f.validate(val) || val.length > f.max) {
        markInvalid(f.$el, f.msg);
        f.$el.focus();
        return;
      }
    }
    if (pwdProt) {
      if (!pwdField.validate(pwd) || pwd.length > pwdField.max) {
        markInvalid($pwd, pwdField.msg);
        $pwd.focus();
        return;
      }
    }

    const submitBtn = $form.find("button[type=submit]")[0];
    addSpinnerToButton(submitBtn);

    // Build payload
    const payload = {
      name,
      description: desc,
      shortUrl: url,
      isPublic,
      isPasswordProtected: pwdProt,
    };
    if (pwdProt) payload.password = pwd;

  
    try {
      const resp = await fetch(API + "Links", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error("Request failed");

      createPopup("Link added successfully!");
      setTimeout(() => {
        window.location.href = `profile.html?userID=${currentUser}`;
      }, 1200);
    } catch (err) {
      console.error(err);
      createPopupError("Failed to add link.");
      restoreButton(submitBtn);
    }
  });
});
