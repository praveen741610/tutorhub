(function () {
  var session = window.TutorHubSession;
  var ui = window.TutorHubUI;
  if (!session) {
    return;
  }

  var form = document.getElementById("auth-form");
  var message = document.getElementById("message");
  var submitButton = document.getElementById("submit-button");
  var tokenPanel = document.getElementById("token-panel");
  var tokenField = document.getElementById("token-field");
  var docsButton = document.getElementById("docs-button");
  var logoutButton = document.getElementById("logout-button");
  var mode = document.body.dataset.mode;

  if (!form || !message || !submitButton || !mode) {
    return;
  }

  function setMessage(type, text) {
    message.className = "message " + type;
    message.textContent = text;
    if (ui && typeof ui.toast === "function") {
      ui.toast(text, type === "ok" ? "success" : type);
    }
  }

  function clearMessage() {
    message.className = "message";
    message.textContent = "";
  }

  function showToken(token) {
    if (!tokenPanel || !tokenField) {
      return;
    }
    tokenField.value = token || "";
    tokenPanel.classList.toggle("visible", Boolean(token));
  }

  function errorText(payload) {
    if (!payload) {
      return "Request failed.";
    }
    if (payload.error && typeof payload.error.message === "string") {
      return payload.error.message;
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map(function (item) {
        return item.msg || JSON.stringify(item);
      }).join("; ");
    }
    return "Request failed.";
  }

  async function parseResponse(response) {
    var text = await response.text();
    if (!text) {
      return {};
    }
    try {
      return JSON.parse(text);
    } catch (_err) {
      return { detail: text };
    }
  }

  async function doRegister() {
    var role = document.getElementById("role").value;
    var coppaConsent = Boolean(document.getElementById("coppa-consent") && document.getElementById("coppa-consent").checked);
    var communicationOptIn = !document.getElementById("communication-opt-in") || document.getElementById("communication-opt-in").checked;
    if (role === "parent" && !coppaConsent) {
      throw new Error("COPPA consent is required for parent registration.");
    }

    var payload = {
      name: document.getElementById("name").value.trim(),
      email: document.getElementById("email").value.trim(),
      password: document.getElementById("password").value,
      role: role,
      coppa_consent: coppaConsent,
      communication_opt_in: communicationOptIn
    };

    var response = await fetch("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    var data = await parseResponse(response);

    if (!response.ok) {
      throw new Error(errorText(data));
    }

    setMessage("ok", "Registration complete. You can log in now.");
    form.reset();
  }

  async function doLogin() {
    var email = document.getElementById("email").value.trim();
    var password = document.getElementById("password").value;
    var body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    var response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString()
    });
    var data = await parseResponse(response);

    if (!response.ok) {
      throw new Error(errorText(data));
    }

    session.saveSession(data);
    showToken(session.getAccessToken() || "");
    setMessage("ok", "Login successful. Redirecting...");

    var role = (data.role || session.getRole() || "").toLowerCase();
    var nextPath = session.roleHomePath(role);
    window.setTimeout(function () {
      window.location.assign(nextPath);
    }, 450);
  }

  async function maybeRedirectAuthenticatedUser() {
    if (mode !== "login") {
      return;
    }
    var token = await session.ensureAccessToken();
    if (!token) {
      showToken("");
      return;
    }

    showToken(token);
    var role = session.getRole();
    if (!role) {
      await session.refreshSession();
      role = session.getRole();
    }
    if (role) {
      window.location.replace(session.roleHomePath(role));
    }
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    clearMessage();
    submitButton.disabled = true;
    var originalText = submitButton.textContent;
    submitButton.textContent = "Please wait...";

    try {
      if (mode === "register") {
        await doRegister();
      } else if (mode === "login") {
        await doLogin();
      } else {
        throw new Error("Unknown page mode.");
      }
    } catch (error) {
      setMessage("error", error.message || "Something went wrong.");
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = originalText;
    }
  });

  if (docsButton) {
    docsButton.addEventListener("click", function () {
      window.location.assign("/docs");
    });
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", async function () {
      await session.logout();
      showToken("");
      setMessage("ok", "Logged out.");
    });
  }

  showToken(session.getAccessToken() || "");
  maybeRedirectAuthenticatedUser();
})();
