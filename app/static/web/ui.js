(function () {
  var containerId = "tutorhub-toast-container";

  function ensureContainer() {
    var container = document.getElementById(containerId);
    if (container) {
      return container;
    }
    container = document.createElement("div");
    container.id = containerId;
    container.className = "toast-container";
    document.body.appendChild(container);
    return container;
  }

  function toast(message, type) {
    var container = ensureContainer();
    var item = document.createElement("div");
    item.className = "toast " + (type || "info");
    item.textContent = message;
    container.appendChild(item);

    window.setTimeout(function () {
      item.classList.add("hide");
      window.setTimeout(function () {
        if (item.parentElement) {
          item.parentElement.removeChild(item);
        }
      }, 220);
    }, 2600);
  }

  function setSkeleton(target, loading) {
    if (!target) {
      return;
    }
    target.classList.toggle("skeleton-active", Boolean(loading));
  }

  window.TutorHubUI = {
    toast: toast,
    setSkeleton: setSkeleton,
  };
})();
