const OAUTH_CODE_KEY = "spotify_oauth_code";

export function clearOAuthStorage() {
  sessionStorage.removeItem(OAUTH_CODE_KEY);
  sessionStorage.removeItem("session_id");
  Object.keys(sessionStorage).forEach((key) => {
    if (key.startsWith("oauth_session_")) {
      sessionStorage.removeItem(key);
    }
  });
}

export { OAUTH_CODE_KEY };
