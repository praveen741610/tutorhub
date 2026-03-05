(function () {
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
    trialForm.addEventListener("submit", function (event) {
      event.preventDefault();
      var note = document.getElementById("trial-note");
      if (note) {
        note.textContent = "Thanks! Our admissions team will contact you within 24 hours.";
      }
      trialForm.reset();
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
