import { Capacitor } from "@capacitor/core";
import { runNativeSQLiteSmokeTest } from "./nativeSmokeTest.js";

const ELEMENT_ID =
  "sipucol-field-native-diagnostics";

function createBadge() {
  const existing =
    document.getElementById(ELEMENT_ID);

  if (existing) {
    return existing;
  }

  const badge =
    document.createElement("div");

  badge.id = ELEMENT_ID;

  badge.textContent =
    "FIELD · probando SQLite...";

  Object.assign(
    badge.style,
    {
      position: "fixed",
      right: "10px",
      bottom: "10px",
      zIndex: "2147483647",
      padding: "8px 12px",
      borderRadius: "10px",
      fontFamily:
        "system-ui, sans-serif",
      fontSize: "12px",
      fontWeight: "700",
      color: "white",
      background: "#444",
      boxShadow:
        "0 2px 10px rgba(0,0,0,.35)",
      pointerEvents: "none",
      maxWidth: "80vw",
    }
  );

  document.body.appendChild(badge);

  return badge;
}

async function runDiagnostics() {
  if (!Capacitor.isNativePlatform()) {
    return;
  }

  const badge = createBadge();

  try {
    const result =
      await runNativeSQLiteSmokeTest();

    const networkText =
      result.connected
        ? "ONLINE"
        : "OFFLINE";

    if (result.passed) {
      badge.textContent =
        `FIELD · SQLite OK · ${networkText}`;

      badge.style.background =
        "#166534";
    } else {
      badge.textContent =
        "FIELD · SQLite ERROR";

      badge.style.background =
        "#991b1b";
    }
  } catch (error) {
    badge.textContent =
      "FIELD · ERROR DE DIAGNOSTICO";

    badge.style.background =
      "#991b1b";

    console.error(
      "[FIELD_NATIVE_DIAGNOSTICS_ERROR]",
      error
    );
  }
}

function start() {
  setTimeout(
    () => {
      runDiagnostics();
    },
    800
  );
}

if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    start,
    { once: true }
  );
} else {
  start();
}