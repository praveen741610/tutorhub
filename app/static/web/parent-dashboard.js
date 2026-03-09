(function () {
  var session = window.TutorHubSession;
  if (!session) {
    window.location.replace("/login");
    return;
  }

  var logoutButton = document.getElementById("logout-button");
  var refreshDashboardButton = document.getElementById("refresh-dashboard-button");
  var dashboardState = document.getElementById("dashboard-state");
  var dashboardJson = document.getElementById("dashboard-json");

  var trialForm = document.getElementById("trial-form");
  var trialState = document.getElementById("trial-state");
  var trialProgram = document.getElementById("trial-program");
  var trialKind = document.getElementById("trial-kind");
  var trialChildName = document.getElementById("trial-child-name");
  var trialChildGrade = document.getElementById("trial-child-grade");
  var trialStart = document.getElementById("trial-start");
  var trialEnd = document.getElementById("trial-end");
  var trialNotes = document.getElementById("trial-notes");

  var enrollmentForm = document.getElementById("enrollment-form");
  var enrollmentState = document.getElementById("enrollment-state");
  var enrollmentProgram = document.getElementById("enrollment-program");
  var enrollmentPlan = document.getElementById("enrollment-plan");
  var enrollmentChildName = document.getElementById("enrollment-child-name");
  var enrollmentChildGrade = document.getElementById("enrollment-child-grade");

  function setState(node, text, kind) {
    if (!node) {
      return;
    }
    node.classList.remove("error");
    node.classList.remove("success");
    if (kind === "error") {
      node.classList.add("error");
    } else if (kind === "success") {
      node.classList.add("success");
    }
    node.textContent = text;
  }

  function toDateInputValue(date) {
    function pad(value) {
      return String(value).padStart(2, "0");
    }
    return (
      date.getFullYear() + "-" +
      pad(date.getMonth() + 1) + "-" +
      pad(date.getDate()) + "T" +
      pad(date.getHours()) + ":" +
      pad(date.getMinutes())
    );
  }

  function parseDateInputValue(value) {
    if (!value) {
      return null;
    }
    var parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return parsed;
  }

  function toApiDateTime(value) {
    if (!value) {
      return "";
    }
    return value.length === 16 ? value + ":00" : value;
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

  function readErrorText(payload, fallback) {
    if (!payload) {
      return fallback;
    }
    if (payload.error && payload.error.message) {
      return payload.error.message;
    }
    if (payload.detail) {
      if (typeof payload.detail === "string") {
        return payload.detail;
      }
      if (Array.isArray(payload.detail)) {
        return payload.detail.map(function (item) { return item.msg || JSON.stringify(item); }).join("; ");
      }
    }
    return fallback;
  }

  async function fetchJson(url, options, fallbackError) {
    var response = await session.authFetch(url, options || {});
    var payload = await parseResponse(response);
    if (response.status === 401) {
      window.location.replace("/login");
      throw new Error("Session expired. Please log in again.");
    }
    if (!response.ok) {
      throw new Error(readErrorText(payload, fallbackError));
    }
    return payload;
  }

  function applyTrialDuration() {
    var start = parseDateInputValue(trialStart.value);
    if (!start) {
      return;
    }
    var duration = trialKind.value === "consultation" ? 30 : 45;
    var end = new Date(start.getTime() + duration * 60 * 1000);
    trialEnd.value = toDateInputValue(end);
  }

  function applyTrialDefaults() {
    var now = new Date();
    now.setMinutes(0, 0, 0);
    now.setHours(now.getHours() + 1);
    trialStart.value = toDateInputValue(now);
    applyTrialDuration();
  }

  async function loadDashboard() {
    setState(dashboardState, "Loading dashboard...", "info");
    try {
      var data = await fetchJson("/academy/dashboard", {}, "Could not load parent dashboard.");
      dashboardJson.textContent = JSON.stringify(data, null, 2);
      setState(dashboardState, "Dashboard loaded.", "success");
    } catch (error) {
      dashboardJson.textContent = "";
      setState(dashboardState, error.message || "Could not load dashboard.", "error");
    }
  }

  async function submitTrial(event) {
    event.preventDefault();
    setState(trialState, "Booking slot...", "info");

    var payload = {
      program_slug: trialProgram.value,
      booking_kind: trialKind.value,
      child_name: trialChildName.value.trim(),
      child_grade: trialChildGrade.value.trim(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York",
      slot_start: toApiDateTime(trialStart.value),
      slot_end: toApiDateTime(trialEnd.value),
      notes: trialNotes.value.trim()
    };

    try {
      var booked = await fetchJson(
        "/academy/trials/book",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        },
        "Could not book slot."
      );
      setState(trialState, "Booked. Meeting link: " + booked.meeting_link, "success");
      trialNotes.value = "";
      await loadDashboard();
    } catch (error) {
      setState(trialState, error.message || "Could not book slot.", "error");
    }
  }

  async function submitEnrollment(event) {
    event.preventDefault();
    setState(enrollmentState, "Creating enrollment...", "info");
    var payload = {
      program_slug: enrollmentProgram.value,
      plan_type: enrollmentPlan.value,
      child_name: enrollmentChildName.value.trim(),
      child_grade: enrollmentChildGrade.value.trim()
    };

    try {
      var created = await fetchJson(
        "/academy/enrollments",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        },
        "Could not create enrollment."
      );
      setState(
        enrollmentState,
        "Enrollment created. Final cycle price: $" + created.final_price_usd + " USD.",
        "success"
      );
      await loadDashboard();
    } catch (error) {
      setState(enrollmentState, error.message || "Could not create enrollment.", "error");
    }
  }

  async function init() {
    var hasSession = await session.requireSession("parent");
    if (!hasSession) {
      return;
    }
    applyTrialDefaults();
    loadDashboard();
  }

  if (trialKind) {
    trialKind.addEventListener("change", applyTrialDuration);
  }
  if (trialStart) {
    trialStart.addEventListener("change", applyTrialDuration);
  }
  if (trialForm) {
    trialForm.addEventListener("submit", submitTrial);
  }
  if (enrollmentForm) {
    enrollmentForm.addEventListener("submit", submitEnrollment);
  }
  if (refreshDashboardButton) {
    refreshDashboardButton.addEventListener("click", loadDashboard);
  }
  if (logoutButton) {
    logoutButton.addEventListener("click", async function () {
      await session.logout();
      window.location.replace("/login");
    });
  }

  init();
})();
