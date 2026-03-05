(function () {
  var session = window.TutorHubSession;
  var ui = window.TutorHubUI;
  if (!session) {
    window.location.replace("/login");
    return;
  }

  var tokenField = document.getElementById("token-field");
  var logoutButton = document.getElementById("logout-button");
  var dashboardRole = String(document.body.dataset.dashboardRole || "").toLowerCase();

  function updateTokenField() {
    if (!tokenField) {
      return;
    }
    tokenField.value = session.getAccessToken() || "";
  }

  function setState(element, text, kind) {
    if (!element) {
      return;
    }
    element.textContent = text;
    element.classList.remove("error");
    element.classList.remove("success");
    if (kind === "error") {
      element.classList.add("error");
    } else if (kind === "success") {
      element.classList.add("success");
    }
  }

  function notify(message, type) {
    if (ui && typeof ui.toast === "function") {
      ui.toast(message, type || "info");
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll("\"", "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatDateTime(value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value || "-";
    }
    return new Intl.DateTimeFormat(undefined, {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    }).format(date);
  }

  function toDateInputValue(date) {
    function pad(number) {
      return String(number).padStart(2, "0");
    }
    return (
      date.getFullYear() + "-" +
      pad(date.getMonth() + 1) + "-" +
      pad(date.getDate()) + "T" +
      pad(date.getHours()) + ":" +
      pad(date.getMinutes())
    );
  }

  function getSortedItems(items, sortOrder) {
    var sorted = items.slice();
    if (sortOrder === "start_asc") {
      sorted.sort(function (a, b) { return new Date(a.slot_start).getTime() - new Date(b.slot_start).getTime(); });
      return sorted;
    }
    if (sortOrder === "id_asc") {
      sorted.sort(function (a, b) { return Number(a.id) - Number(b.id); });
      return sorted;
    }
    if (sortOrder === "id_desc") {
      sorted.sort(function (a, b) { return Number(b.id) - Number(a.id); });
      return sorted;
    }
    sorted.sort(function (a, b) { return new Date(b.slot_start).getTime() - new Date(a.slot_start).getTime(); });
    return sorted;
  }

  function statusClass(status) {
    var normalized = String(status || "").toLowerCase();
    if (normalized === "requested" || normalized === "accepted" || normalized === "rejected" || normalized === "canceled") {
      return "status-" + normalized;
    }
    return "";
  }

  function renderStats(container, items) {
    if (!container) {
      return;
    }
    var counts = {
      total: items.length,
      requested: 0,
      accepted: 0,
      rejected: 0,
      canceled: 0
    };
    items.forEach(function (item) {
      var key = String(item.status || "").toLowerCase();
      if (Object.prototype.hasOwnProperty.call(counts, key)) {
        counts[key] += 1;
      }
    });
    var labels = [
      ["total", "Total"],
      ["requested", "Requested"],
      ["accepted", "Accepted"],
      ["rejected", "Rejected"],
      ["canceled", "Canceled"]
    ];
    container.innerHTML = labels.map(function (entry) {
      var key = entry[0];
      var label = entry[1];
      return (
        "<article class=\"stat-card\">" +
          "<p class=\"stat-label\">" + label + "</p>" +
          "<p class=\"stat-value\">" + counts[key] + "</p>" +
        "</article>"
      );
    }).join("");
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
    return fallback;
  }

  function toApiDateTime(value) {
    if (!value) {
      return "";
    }
    return value.length === 16 ? value + ":00" : value;
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
    updateTokenField();
    return payload;
  }

  function initStudentDashboard() {
    var refreshButton = document.getElementById("refresh-bookings-button");
    var stateElement = document.getElementById("bookings-state");
    var statsElement = document.getElementById("booking-stats");
    var tableElement = document.getElementById("bookings-table");
    var tableWrapElement = tableElement ? tableElement.closest(".table-wrap") : null;
    var rowsElement = document.getElementById("booking-rows");
    var statusFilterElement = document.getElementById("student-status-filter");
    var sortOrderElement = document.getElementById("student-sort-order");

    var bookingForm = document.getElementById("booking-form");
    var bookingFormState = document.getElementById("booking-form-state");
    var refreshTutorsButton = document.getElementById("refresh-tutors-button");
    var createBookingButton = document.getElementById("create-booking-button");
    var tutorSelect = document.getElementById("tutor-select");
    var slotStartInput = document.getElementById("slot-start");
    var slotEndInput = document.getElementById("slot-end");
    var bookingMessageInput = document.getElementById("booking-message");

    var allBookings = [];

    function ensureDefaultSlotValues() {
      if (!slotStartInput || !slotEndInput) {
        return;
      }
      if (slotStartInput.value && slotEndInput.value) {
        return;
      }
      var start = new Date();
      start.setMinutes(0, 0, 0);
      start.setHours(start.getHours() + 1);
      var end = new Date(start.getTime() + 60 * 60 * 1000);
      slotStartInput.value = toDateInputValue(start);
      slotEndInput.value = toDateInputValue(end);
    }

    function formatTutorOptionLabel(tutor) {
      var name = tutor.name || "Tutor";
      var rate = typeof tutor.hourly_rate === "number" ? "$" + tutor.hourly_rate + "/hr" : "$0/hr";
      var subjects = tutor.subjects ? tutor.subjects : "no subjects listed";
      return "#" + tutor.tutor_id + " - " + name + " - " + rate + " - " + subjects;
    }

    function setTutorOptions(tutors) {
      if (!tutorSelect) {
        return;
      }
      tutorSelect.innerHTML = "";

      if (!tutors.length) {
        var emptyOption = document.createElement("option");
        emptyOption.value = "";
        emptyOption.textContent = "No active tutors available";
        tutorSelect.appendChild(emptyOption);
        tutorSelect.disabled = true;
        if (createBookingButton) {
          createBookingButton.disabled = true;
        }
        return;
      }

      tutors.forEach(function (tutor) {
        var option = document.createElement("option");
        option.value = String(tutor.tutor_id);
        option.textContent = formatTutorOptionLabel(tutor);
        tutorSelect.appendChild(option);
      });

      tutorSelect.disabled = false;
      if (createBookingButton) {
        createBookingButton.disabled = false;
      }
    }

    function getVisibleBookings() {
      var statusFilter = statusFilterElement ? statusFilterElement.value : "all";
      var sortOrder = sortOrderElement ? sortOrderElement.value : "start_desc";
      var filtered = allBookings.filter(function (booking) {
        if (statusFilter === "all") {
          return true;
        }
        return String(booking.status || "").toLowerCase() === statusFilter;
      });
      return getSortedItems(filtered, sortOrder);
    }

    function renderStudentRows(visibleBookings) {
      if (!rowsElement || !tableElement) {
        return;
      }

      if (!allBookings.length) {
        tableElement.hidden = true;
        rowsElement.innerHTML = "";
        setState(stateElement, "No booking requests yet.", "info");
        return;
      }

      if (!visibleBookings.length) {
        tableElement.hidden = true;
        rowsElement.innerHTML = "";
        setState(stateElement, "No booking requests match current filters.", "info");
        return;
      }

      rowsElement.innerHTML = visibleBookings.map(function (booking) {
        var status = booking.status || "-";
        var message = booking.message || "-";
        var cls = statusClass(status);
        var canCancel = String(status).toLowerCase() === "requested";
        var actions = canCancel
          ? "<button class=\"btn sm danger\" type=\"button\" data-action=\"cancel\" data-request-id=\"" + escapeHtml(booking.id) + "\">Cancel</button>"
          : "<button class=\"btn sm ghost\" type=\"button\" disabled>No Action</button>";

        return (
          "<tr>" +
            "<td>" + escapeHtml(booking.id) + "</td>" +
            "<td>" + escapeHtml(booking.tutor_id) + "</td>" +
            "<td>" + escapeHtml(formatDateTime(booking.slot_start)) + "</td>" +
            "<td>" + escapeHtml(formatDateTime(booking.slot_end)) + "</td>" +
            "<td><span class=\"status-badge " + cls + "\">" + escapeHtml(status) + "</span></td>" +
            "<td>" + escapeHtml(message) + "</td>" +
            "<td><div class=\"table-actions\">" + actions + "</div></td>" +
          "</tr>"
        );
      }).join("");

      tableElement.hidden = false;
      setState(stateElement, "Showing " + visibleBookings.length + " of " + allBookings.length + " booking request(s).", "info");
    }

    function renderStudentBookings() {
      renderStats(statsElement, allBookings);
      renderStudentRows(getVisibleBookings());
    }

    async function loadTutors() {
      if (refreshTutorsButton) {
        refreshTutorsButton.disabled = true;
      }
      setState(bookingFormState, "Loading tutors...", "info");
      if (ui) {
        ui.setSkeleton(bookingForm, true);
      }

      try {
        var tutors = await fetchJson("/tutors", {}, "Could not load tutors.");
        if (!Array.isArray(tutors)) {
          throw new Error("Unexpected response while loading tutors.");
        }
        setTutorOptions(tutors);
        if (tutors.length) {
          setState(bookingFormState, "Loaded " + tutors.length + " active tutor(s).", "info");
        } else {
          setState(bookingFormState, "No active tutors found. Ask a tutor to set up a profile.", "error");
          notify("No active tutors found.", "error");
        }
      } catch (error) {
        setTutorOptions([]);
        setState(bookingFormState, error.message || "Could not load tutors.", "error");
        notify(error.message || "Could not load tutors.", "error");
      } finally {
        if (refreshTutorsButton) {
          refreshTutorsButton.disabled = false;
        }
        if (ui) {
          ui.setSkeleton(bookingForm, false);
        }
      }
    }

    async function loadStudentBookings() {
      if (refreshButton) {
        refreshButton.disabled = true;
      }
      setState(stateElement, "Loading bookings...", "info");
      if (ui) {
        ui.setSkeleton(statsElement, true);
        ui.setSkeleton(tableWrapElement, true);
      }

      try {
        var bookings = await fetchJson("/bookings/my", {}, "Could not load bookings.");
        if (!Array.isArray(bookings)) {
          throw new Error("Unexpected response while loading bookings.");
        }
        allBookings = bookings;
        renderStudentBookings();
      } catch (error) {
        allBookings = [];
        renderStudentBookings();
        setState(stateElement, error.message || "Could not load bookings.", "error");
        notify(error.message || "Could not load bookings.", "error");
      } finally {
        if (refreshButton) {
          refreshButton.disabled = false;
        }
        if (ui) {
          ui.setSkeleton(statsElement, false);
          ui.setSkeleton(tableWrapElement, false);
        }
      }
    }

    async function cancelBookingRequest(requestId) {
      setState(stateElement, "Canceling booking request #" + requestId + "...", "info");
      var snapshot = allBookings.map(function (item) { return Object.assign({}, item); });
      allBookings = allBookings.map(function (item) {
        if (Number(item.id) === Number(requestId)) {
          return Object.assign({}, item, { status: "canceled" });
        }
        return item;
      });
      renderStudentBookings();
      try {
        await fetchJson("/bookings/" + requestId + "/cancel", { method: "POST" }, "Could not cancel booking request.");
        setState(stateElement, "Booking request #" + requestId + " canceled.", "success");
        notify("Booking request #" + requestId + " canceled.", "success");
        await loadStudentBookings();
      } catch (error) {
        allBookings = snapshot;
        renderStudentBookings();
        setState(stateElement, error.message || "Could not cancel booking request.", "error");
        notify(error.message || "Could not cancel booking request.", "error");
      }
    }

    async function createBooking(event) {
      event.preventDefault();
      if (!tutorSelect || !slotStartInput || !slotEndInput || !bookingMessageInput) {
        return;
      }

      var tutorId = Number(tutorSelect.value);
      var slotStart = toApiDateTime(slotStartInput.value);
      var slotEnd = toApiDateTime(slotEndInput.value);
      var message = bookingMessageInput.value.trim();

      if (!tutorId) {
        setState(bookingFormState, "Select a tutor first.", "error");
        return;
      }
      if (!slotStart || !slotEnd) {
        setState(bookingFormState, "Provide both start and end time.", "error");
        return;
      }

      var originalText = createBookingButton ? createBookingButton.textContent : "Send Booking Request";
      if (createBookingButton) {
        createBookingButton.disabled = true;
        createBookingButton.textContent = "Submitting...";
      }
      setState(bookingFormState, "Submitting booking request...", "info");

      try {
        var payload = {
          tutor_id: tutorId,
          slot_start: slotStart,
          slot_end: slotEnd,
          message: message
        };
        var created = await fetchJson(
          "/bookings/request",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          },
          "Could not create booking request."
        );
        setState(bookingFormState, "Booking request created (ID #" + created.id + ").", "success");
        notify("Booking request #" + created.id + " created.", "success");
        bookingMessageInput.value = "";
        ensureDefaultSlotValues();
        await loadStudentBookings();
      } catch (error) {
        setState(bookingFormState, error.message || "Could not create booking request.", "error");
        notify(error.message || "Could not create booking request.", "error");
      } finally {
        if (createBookingButton) {
          createBookingButton.disabled = false;
          createBookingButton.textContent = originalText;
        }
      }
    }

    if (refreshButton) {
      refreshButton.addEventListener("click", loadStudentBookings);
    }
    if (refreshTutorsButton) {
      refreshTutorsButton.addEventListener("click", loadTutors);
    }
    if (bookingForm) {
      bookingForm.addEventListener("submit", createBooking);
    }
    if (statusFilterElement) {
      statusFilterElement.addEventListener("change", renderStudentBookings);
    }
    if (sortOrderElement) {
      sortOrderElement.addEventListener("change", renderStudentBookings);
    }
    if (rowsElement) {
      rowsElement.addEventListener("click", function (event) {
        var button = event.target.closest("button[data-action='cancel']");
        if (!button) {
          return;
        }
        var requestId = Number(button.dataset.requestId);
        if (!requestId) {
          return;
        }
        cancelBookingRequest(requestId);
      });
    }

    ensureDefaultSlotValues();
    loadTutors();
    loadStudentBookings();
  }

  function initTutorDashboard() {
    var profileForm = document.getElementById("profile-form");
    var profileState = document.getElementById("profile-state");
    var reloadProfileButton = document.getElementById("reload-profile-button");
    var saveProfileButton = document.getElementById("save-profile-button");
    var profileHeadline = document.getElementById("profile-headline");
    var profileBio = document.getElementById("profile-bio");
    var profileRate = document.getElementById("profile-hourly-rate");
    var profileSubjects = document.getElementById("profile-subjects");
    var profileLanguages = document.getElementById("profile-languages");
    var profileTimezone = document.getElementById("profile-timezone");

    var availabilityForm = document.getElementById("availability-form");
    var availabilityState = document.getElementById("availability-state");
    var availabilityStart = document.getElementById("availability-start");
    var availabilityEnd = document.getElementById("availability-end");
    var addAvailabilityButton = document.getElementById("add-availability-button");

    var refreshButton = document.getElementById("refresh-tutor-requests-button");
    var stateElement = document.getElementById("tutor-requests-state");
    var statsElement = document.getElementById("tutor-request-stats");
    var tableElement = document.getElementById("tutor-requests-table");
    var tableWrapElement = tableElement ? tableElement.closest(".table-wrap") : null;
    var rowsElement = document.getElementById("tutor-request-rows");
    var statusFilterElement = document.getElementById("tutor-status-filter");
    var sortOrderElement = document.getElementById("tutor-sort-order");

    var allRequests = [];

    function ensureDefaultAvailabilityValues() {
      if (!availabilityStart || !availabilityEnd) {
        return;
      }
      if (availabilityStart.value && availabilityEnd.value) {
        return;
      }
      var start = new Date();
      start.setMinutes(0, 0, 0);
      start.setHours(start.getHours() + 1);
      var end = new Date(start.getTime() + 60 * 60 * 1000);
      availabilityStart.value = toDateInputValue(start);
      availabilityEnd.value = toDateInputValue(end);
    }

    function applyProfileValues(profile) {
      if (!profileHeadline) {
        return;
      }
      profileHeadline.value = profile.headline || "";
      profileBio.value = profile.bio || "";
      profileRate.value = typeof profile.hourly_rate === "number" ? String(profile.hourly_rate) : "0";
      profileSubjects.value = profile.subjects || "";
      profileLanguages.value = profile.languages || "";
      profileTimezone.value = profile.timezone || "UTC";
    }

    async function loadProfile() {
      if (reloadProfileButton) {
        reloadProfileButton.disabled = true;
      }
      setState(profileState, "Loading profile...", "info");
      if (ui) {
        ui.setSkeleton(profileForm, true);
      }
      try {
        var profile = await fetchJson("/tutor/profile", {}, "Could not load profile.");
        applyProfileValues(profile);
        setState(profileState, "Profile loaded.", "success");
      } catch (error) {
        setState(profileState, error.message || "Could not load profile.", "error");
        notify(error.message || "Could not load profile.", "error");
      } finally {
        if (reloadProfileButton) {
          reloadProfileButton.disabled = false;
        }
        if (ui) {
          ui.setSkeleton(profileForm, false);
        }
      }
    }

    async function saveProfile(event) {
      event.preventDefault();
      if (!profileHeadline || !profileBio || !profileRate || !profileSubjects || !profileLanguages || !profileTimezone) {
        return;
      }

      var payload = {
        headline: profileHeadline.value.trim(),
        bio: profileBio.value.trim(),
        hourly_rate: Number(profileRate.value || 0),
        subjects: profileSubjects.value.trim(),
        languages: profileLanguages.value.trim(),
        timezone: profileTimezone.value.trim() || "UTC"
      };

      var originalText = saveProfileButton ? saveProfileButton.textContent : "Save Profile";
      if (saveProfileButton) {
        saveProfileButton.disabled = true;
        saveProfileButton.textContent = "Saving...";
      }
      setState(profileState, "Saving profile...", "info");

      try {
        await fetchJson(
          "/tutor/profile",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          },
          "Could not save profile."
        );
        setState(profileState, "Profile saved.", "success");
        notify("Tutor profile saved.", "success");
      } catch (error) {
        setState(profileState, error.message || "Could not save profile.", "error");
        notify(error.message || "Could not save profile.", "error");
      } finally {
        if (saveProfileButton) {
          saveProfileButton.disabled = false;
          saveProfileButton.textContent = originalText;
        }
      }
    }

    async function addAvailability(event) {
      event.preventDefault();
      if (!availabilityStart || !availabilityEnd) {
        return;
      }

      var payload = {
        start_time: toApiDateTime(availabilityStart.value),
        end_time: toApiDateTime(availabilityEnd.value)
      };

      if (!payload.start_time || !payload.end_time) {
        setState(availabilityState, "Provide both start and end time.", "error");
        return;
      }

      var originalText = addAvailabilityButton ? addAvailabilityButton.textContent : "Add Availability Slot";
      if (addAvailabilityButton) {
        addAvailabilityButton.disabled = true;
        addAvailabilityButton.textContent = "Adding...";
      }
      setState(availabilityState, "Adding availability slot...", "info");

      try {
        var result = await fetchJson(
          "/tutor/availability",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          },
          "Could not add availability slot."
        );
        setState(availabilityState, "Availability slot added (ID #" + result.id + ").", "success");
        notify("Availability slot added.", "success");
        ensureDefaultAvailabilityValues();
      } catch (error) {
        setState(availabilityState, error.message || "Could not add availability slot.", "error");
        notify(error.message || "Could not add availability slot.", "error");
      } finally {
        if (addAvailabilityButton) {
          addAvailabilityButton.disabled = false;
          addAvailabilityButton.textContent = originalText;
        }
      }
    }

    function getVisibleRequests() {
      var statusFilter = statusFilterElement ? statusFilterElement.value : "all";
      var sortOrder = sortOrderElement ? sortOrderElement.value : "start_desc";
      var filtered = allRequests.filter(function (requestItem) {
        if (statusFilter === "all") {
          return true;
        }
        return String(requestItem.status || "").toLowerCase() === statusFilter;
      });
      return getSortedItems(filtered, sortOrder);
    }

    function renderTutorRows(visibleRequests) {
      if (!rowsElement || !tableElement) {
        return;
      }

      if (!allRequests.length) {
        tableElement.hidden = true;
        rowsElement.innerHTML = "";
        setState(stateElement, "No booking requests yet.", "info");
        return;
      }
      if (!visibleRequests.length) {
        tableElement.hidden = true;
        rowsElement.innerHTML = "";
        setState(stateElement, "No booking requests match current filters.", "info");
        return;
      }

      rowsElement.innerHTML = visibleRequests.map(function (requestItem) {
        var status = requestItem.status || "-";
        var message = requestItem.message || "-";
        var cls = statusClass(status);
        var studentLabel = "#" + requestItem.student_id + (requestItem.student_name ? " - " + requestItem.student_name : "");
        var canAct = String(status).toLowerCase() === "requested";
        var actions = canAct
          ? (
            "<button class=\"btn sm success\" type=\"button\" data-action=\"accept\" data-request-id=\"" + escapeHtml(requestItem.id) + "\">Accept</button>" +
            "<button class=\"btn sm danger\" type=\"button\" data-action=\"reject\" data-request-id=\"" + escapeHtml(requestItem.id) + "\">Reject</button>"
          )
          : "<button class=\"btn sm ghost\" type=\"button\" disabled>No Action</button>";

        return (
          "<tr>" +
            "<td>" + escapeHtml(requestItem.id) + "</td>" +
            "<td>" + escapeHtml(studentLabel) + "</td>" +
            "<td>" + escapeHtml(formatDateTime(requestItem.slot_start)) + "</td>" +
            "<td>" + escapeHtml(formatDateTime(requestItem.slot_end)) + "</td>" +
            "<td><span class=\"status-badge " + cls + "\">" + escapeHtml(status) + "</span></td>" +
            "<td>" + escapeHtml(message) + "</td>" +
            "<td><div class=\"table-actions\">" + actions + "</div></td>" +
          "</tr>"
        );
      }).join("");

      tableElement.hidden = false;
      setState(stateElement, "Showing " + visibleRequests.length + " of " + allRequests.length + " request(s).", "info");
    }

    function renderTutorRequests() {
      renderStats(statsElement, allRequests);
      renderTutorRows(getVisibleRequests());
    }

    async function loadTutorRequests() {
      if (refreshButton) {
        refreshButton.disabled = true;
      }
      setState(stateElement, "Loading requests...", "info");
      if (ui) {
        ui.setSkeleton(statsElement, true);
        ui.setSkeleton(tableWrapElement, true);
      }

      try {
        var requests = await fetchJson("/tutor/requests", {}, "Could not load tutor requests.");
        if (!Array.isArray(requests)) {
          throw new Error("Unexpected response while loading tutor requests.");
        }
        allRequests = requests;
        renderTutorRequests();
      } catch (error) {
        allRequests = [];
        renderTutorRequests();
        setState(stateElement, error.message || "Could not load tutor requests.", "error");
        notify(error.message || "Could not load tutor requests.", "error");
      } finally {
        if (refreshButton) {
          refreshButton.disabled = false;
        }
        if (ui) {
          ui.setSkeleton(statsElement, false);
          ui.setSkeleton(tableWrapElement, false);
        }
      }
    }

    async function updateTutorRequest(requestId, action) {
      var endpoint = action === "accept"
        ? "/tutor/requests/" + requestId + "/accept"
        : "/tutor/requests/" + requestId + "/reject";
      setState(stateElement, "Updating request #" + requestId + "...", "info");
      var nextStatus = action === "accept" ? "accepted" : "rejected";
      var snapshot = allRequests.map(function (item) { return Object.assign({}, item); });
      allRequests = allRequests.map(function (item) {
        if (Number(item.id) === Number(requestId)) {
          return Object.assign({}, item, { status: nextStatus });
        }
        return item;
      });
      renderTutorRequests();

      try {
        await fetchJson(endpoint, { method: "POST" }, "Could not update request.");
        setState(stateElement, "Request #" + requestId + " " + nextStatus + ".", "success");
        notify("Request #" + requestId + " " + nextStatus + ".", "success");
        await loadTutorRequests();
      } catch (error) {
        allRequests = snapshot;
        renderTutorRequests();
        setState(stateElement, error.message || "Could not update request.", "error");
        notify(error.message || "Could not update request.", "error");
      }
    }

    if (profileForm) {
      profileForm.addEventListener("submit", saveProfile);
    }
    if (reloadProfileButton) {
      reloadProfileButton.addEventListener("click", loadProfile);
    }
    if (availabilityForm) {
      availabilityForm.addEventListener("submit", addAvailability);
    }
    if (refreshButton) {
      refreshButton.addEventListener("click", loadTutorRequests);
    }
    if (statusFilterElement) {
      statusFilterElement.addEventListener("change", renderTutorRequests);
    }
    if (sortOrderElement) {
      sortOrderElement.addEventListener("change", renderTutorRequests);
    }
    if (rowsElement) {
      rowsElement.addEventListener("click", function (event) {
        var button = event.target.closest("button[data-action]");
        if (!button) {
          return;
        }
        var action = button.dataset.action;
        var requestId = Number(button.dataset.requestId);
        if (!requestId || (action !== "accept" && action !== "reject")) {
          return;
        }
        updateTutorRequest(requestId, action);
      });
    }

    ensureDefaultAvailabilityValues();
    loadProfile();
    loadTutorRequests();
  }

  async function init() {
    var hasSession = await session.requireSession(dashboardRole || null);
    if (!hasSession) {
      return;
    }
    updateTokenField();

    if (dashboardRole === "student") {
      initStudentDashboard();
    } else if (dashboardRole === "tutor") {
      initTutorDashboard();
    }
  }

  if (logoutButton) {
    logoutButton.addEventListener("click", async function () {
      await session.logout();
      window.location.replace("/login");
    });
  }

  init();
})();
