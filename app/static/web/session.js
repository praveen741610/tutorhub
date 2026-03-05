(function () {
  var ACCESS_KEY = "tutorhub_access_token";
  var REFRESH_KEY = "tutorhub_refresh_token";
  var ROLE_KEY = "tutorhub_user_role";

  function getAccessToken() {
    return window.localStorage.getItem(ACCESS_KEY);
  }

  function getRefreshToken() {
    return window.localStorage.getItem(REFRESH_KEY);
  }

  function getRole() {
    return window.localStorage.getItem(ROLE_KEY) || "";
  }

  function setRole(role) {
    if (role) {
      window.localStorage.setItem(ROLE_KEY, role);
    }
  }

  function clearSession() {
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
    window.localStorage.removeItem(ROLE_KEY);
  }

  function saveSession(payload) {
    if (!payload) {
      return;
    }
    if (payload.access_token) {
      window.localStorage.setItem(ACCESS_KEY, payload.access_token);
    }
    if (payload.refresh_token) {
      window.localStorage.setItem(REFRESH_KEY, payload.refresh_token);
    }
    if (payload.role) {
      setRole(payload.role);
    }
  }

  function parseJwtPayload(token) {
    try {
      var body = token.split(".")[1];
      var base64 = body.replace(/-/g, "+").replace(/_/g, "/");
      var decoded = window.atob(base64);
      return JSON.parse(decoded);
    } catch (_err) {
      return null;
    }
  }

  function isTokenExpired(token, skewSeconds) {
    if (!token) {
      return true;
    }
    var payload = parseJwtPayload(token);
    if (!payload || !payload.exp) {
      return true;
    }
    var now = Math.floor(Date.now() / 1000);
    return payload.exp <= (now + (skewSeconds || 0));
  }

  function roleHomePath(role) {
    return String(role || "").toLowerCase() === "tutor" ? "/tutor/home" : "/student/home";
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

  async function refreshSession() {
    var refreshToken = getRefreshToken();
    if (!refreshToken || isTokenExpired(refreshToken, 30)) {
      clearSession();
      return null;
    }

    try {
      var response = await fetch("/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      var payload = await parseResponse(response);
      if (!response.ok || !payload.access_token) {
        clearSession();
        return null;
      }

      saveSession(payload);
      return payload.access_token;
    } catch (_err) {
      clearSession();
      return null;
    }
  }

  async function logout() {
    var refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearSession();
      return { ok: true };
    }

    try {
      await fetch("/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
    } catch (_err) {}

    clearSession();
    return { ok: true };
  }

  async function logoutAll() {
    var refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearSession();
      return { ok: true, revoked_sessions: 0 };
    }

    try {
      var response = await fetch("/auth/logout-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken })
      });
      var payload = await parseResponse(response);
      clearSession();
      return payload;
    } catch (_err) {
      clearSession();
      return { ok: true, revoked_sessions: 0 };
    }
  }

  async function ensureAccessToken() {
    var accessToken = getAccessToken();
    if (accessToken && !isTokenExpired(accessToken, 30)) {
      return accessToken;
    }
    return await refreshSession();
  }

  async function authFetch(url, options) {
    var requestOptions = options ? Object.assign({}, options) : {};
    var headers = new Headers(requestOptions.headers || {});

    var token = await ensureAccessToken();
    if (!token) {
      return new Response(JSON.stringify({ error: { code: "unauthorized", message: "Session expired" } }), {
        status: 401,
        headers: { "Content-Type": "application/json" }
      });
    }
    headers.set("Authorization", "Bearer " + token);
    requestOptions.headers = headers;

    var response = await fetch(url, requestOptions);
    if (response.status !== 401) {
      return response;
    }

    var refreshed = await refreshSession();
    if (!refreshed) {
      return response;
    }

    var retryHeaders = new Headers(options && options.headers ? options.headers : {});
    retryHeaders.set("Authorization", "Bearer " + refreshed);
    var retryOptions = options ? Object.assign({}, options) : {};
    retryOptions.headers = retryHeaders;
    return fetch(url, retryOptions);
  }

  async function requireSession(role) {
    var token = await ensureAccessToken();
    if (!token) {
      window.location.replace("/login");
      return false;
    }

    var currentRole = getRole();
    if (role && currentRole && currentRole !== role) {
      window.location.replace(roleHomePath(currentRole));
      return false;
    }
    return true;
  }

  window.TutorHubSession = {
    ACCESS_KEY: ACCESS_KEY,
    REFRESH_KEY: REFRESH_KEY,
    ROLE_KEY: ROLE_KEY,
    getAccessToken: getAccessToken,
    getRefreshToken: getRefreshToken,
    getRole: getRole,
    saveSession: saveSession,
    clearSession: clearSession,
    roleHomePath: roleHomePath,
    parseJwtPayload: parseJwtPayload,
    isTokenExpired: isTokenExpired,
    refreshSession: refreshSession,
    logout: logout,
    logoutAll: logoutAll,
    ensureAccessToken: ensureAccessToken,
    authFetch: authFetch,
    requireSession: requireSession,
  };
})();
