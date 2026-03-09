(function () {
  function parseResponseText(text) {
    if (!text) {
      return {};
    }
    try {
      return JSON.parse(text);
    } catch (_err) {
      return { detail: text };
    }
  }

  function readError(payload, fallback) {
    if (!payload) {
      return fallback;
    }
    if (payload.error && payload.error.message) {
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

  function toApiDateTime(value) {
    if (!value) {
      return "";
    }
    return value.length === 16 ? value + ":00" : value;
  }

  var toggle = document.querySelector(".nav-toggle");
  var links = document.querySelector(".nav-links");
  if (toggle && links) {
    toggle.addEventListener("click", function () {
      links.classList.toggle("open");
    });
  }

  var current = window.location.pathname.replace(/\/$/, "") || "/";
  document.querySelectorAll(".nav-links a").forEach(function (anchor) {
    var href = anchor.getAttribute("href").replace(/\/$/, "") || "/";
    if (href === current) {
      anchor.classList.add("active");
    }
  });

  var yearNode = document.getElementById("year");
  if (yearNode) {
    yearNode.textContent = String(new Date().getFullYear());
  }

  var trialForm = document.getElementById("trial-form");
  if (trialForm) {
    var trialKind = document.getElementById("trial-kind");
    var trialStart = document.getElementById("trial-slot-start");
    var trialEnd = document.getElementById("trial-slot-end");
    var timezoneInput = document.getElementById("trial-timezone");

    function syncTrialDuration() {
      if (!trialKind || !trialStart || !trialEnd || !trialStart.value) {
        return;
      }
      var startDate = new Date(trialStart.value);
      if (Number.isNaN(startDate.getTime())) {
        return;
      }
      var minutes = trialKind.value === "consultation" ? 30 : 45;
      trialEnd.value = toDateInputValue(new Date(startDate.getTime() + minutes * 60 * 1000));
    }

    if (trialKind && trialStart && trialEnd) {
      var firstSlot = new Date();
      firstSlot.setMinutes(0, 0, 0);
      firstSlot.setHours(firstSlot.getHours() + 1);
      trialStart.value = toDateInputValue(firstSlot);
      syncTrialDuration();
      trialKind.addEventListener("change", syncTrialDuration);
      trialStart.addEventListener("change", syncTrialDuration);
    }

    if (timezoneInput && !timezoneInput.value) {
      timezoneInput.value = Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York";
    }

    trialForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      var note = document.getElementById("trial-note");
      if (!note) {
        return;
      }

      var hasAcademyFields = Boolean(
        document.getElementById("trial-program") &&
        document.getElementById("trial-kind") &&
        document.getElementById("trial-slot-start") &&
        document.getElementById("trial-slot-end")
      );
      if (!hasAcademyFields) {
        note.textContent = "Thanks! Our admissions team will contact you within 24 hours.";
        trialForm.reset();
        return;
      }

      var token = window.localStorage.getItem("tutorhub_access_token");
      if (!token) {
        note.textContent = "Please log in as a parent first. Then return to this page and submit again.";
        return;
      }

      var consent = document.getElementById("trial-consent");
      if (consent && !consent.checked) {
        note.textContent = "Please confirm parental consent before submitting.";
        return;
      }

      var payload = {
        program_slug: document.getElementById("trial-program").value,
        booking_kind: document.getElementById("trial-kind").value,
        child_name: (document.getElementById("trial-child-name").value || "").trim(),
        child_grade: (document.getElementById("trial-child-grade").value || "").trim(),
        timezone: (document.getElementById("trial-timezone").value || "").trim() || "America/New_York",
        slot_start: toApiDateTime(document.getElementById("trial-slot-start").value),
        slot_end: toApiDateTime(document.getElementById("trial-slot-end").value),
        notes: (document.getElementById("trial-notes").value || "").trim()
      };

      note.textContent = "Submitting booking request...";
      try {
        var response = await fetch("/academy/trials/book", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
          },
          body: JSON.stringify(payload)
        });
        var data = parseResponseText(await response.text());
        if (!response.ok) {
          note.textContent = readError(data, "Booking failed.");
          return;
        }
        note.textContent = "Booked successfully. Meeting link: " + data.meeting_link;
      } catch (_err) {
        note.textContent = "Booking failed. Please try again.";
      }

      if (trialKind) {
        syncTrialDuration();
      }
      if (note) {
        window.scrollTo({ top: note.offsetTop - 120, behavior: "smooth" });
      }
    });
  }

  var contactForm = document.getElementById("contact-form");
  if (contactForm) {
    contactForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var note = document.getElementById("contact-note");
      if (note) {
        note.textContent = "Message received. We will respond during your selected country timing window.";
      }
      contactForm.reset();
    });
  }
})();
