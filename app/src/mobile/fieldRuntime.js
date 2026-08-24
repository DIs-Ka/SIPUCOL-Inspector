import { Capacitor } from "@capacitor/core";
import { CapacitorSQLite } from "@capacitor-community/sqlite";
import { Network } from "@capacitor/network";

const DB_NAME = "sipucol_field";
const DB_VERSION = 1;

let initializationPromise = null;

const SCHEMA = `
CREATE TABLE IF NOT EXISTS field_meta (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS inspections (
    id TEXT PRIMARY KEY NOT NULL,
    bridge_id TEXT,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    payload_json TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    sync_state TEXT NOT NULL DEFAULT 'local',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id TEXT,
    event_type TEXT NOT NULL,
    event_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inspections_updated
ON inspections(updated_at);

CREATE INDEX IF NOT EXISTS idx_sync_status
ON sync_queue(status);
`;

function nowIso() {
  return new Date().toISOString();
}

function nativePlatform() {
  return Capacitor.isNativePlatform();
}

async function ensureNativeDatabase() {
  const connection = await CapacitorSQLite.isConnection({
    database: DB_NAME,
    readonly: false,
  });

  if (!connection.result) {
    await CapacitorSQLite.createConnection({
      database: DB_NAME,
      version: DB_VERSION,
      encrypted: false,
      mode: "no-encryption",
      readonly: false,
    });
  }

  await CapacitorSQLite.open({
    database: DB_NAME,
    readonly: false,
  });

  await CapacitorSQLite.execute({
    database: DB_NAME,
    statements: SCHEMA,
    transaction: true,
    readonly: false,
  });

  await CapacitorSQLite.run({
    database: DB_NAME,
    statement: `
      INSERT INTO field_meta (
        key,
        value,
        updated_at
      )
      VALUES (?, ?, ?)
      ON CONFLICT(key) DO UPDATE SET
        value = excluded.value,
        updated_at = excluded.updated_at
    `,
    values: [
      "schema_version",
      String(DB_VERSION),
      nowIso(),
    ],
    transaction: true,
    readonly: false,
  });
}

async function initialize() {
  if (initializationPromise) {
    return initializationPromise;
  }

  initializationPromise = (async () => {
    const network = await Network.getStatus();

    if (nativePlatform()) {
      await ensureNativeDatabase();
    }

    const result = {
      ready: true,
      version: "0.1.0",
      platform: Capacitor.getPlatform(),
      native: nativePlatform(),
      connected: Boolean(network.connected),
      connectionType: network.connectionType || "unknown",
      storage: nativePlatform()
        ? "sqlite-native"
        : "browser-development-only",
    };

    console.info("[SIPUCOL FIELD READY]", result);

    return result;
  })();

  try {
    return await initializationPromise;
  } catch (error) {
    initializationPromise = null;
    throw error;
  }
}

async function saveInspection(id, payload = {}) {
  await initialize();

  if (!nativePlatform()) {
    throw new Error(
      "saveInspection SQLite solo debe probarse dentro de Android/iOS."
    );
  }

  if (!id) {
    throw new Error("Inspection ID obligatorio.");
  }

  const now = nowIso();

  const existing = await CapacitorSQLite.query({
    database: DB_NAME,
    statement: `
      SELECT revision
      FROM inspections
      WHERE id = ?
      LIMIT 1
    `,
    values: [id],
    readonly: false,
  });

  const row = (existing.values || []).find(
    (item) =>
      item &&
      typeof item === "object" &&
      Object.prototype.hasOwnProperty.call(item, "revision")
  );

  const revision = Number(row?.revision || 0) + 1;

  await CapacitorSQLite.run({
    database: DB_NAME,
    statement: `
      INSERT INTO inspections (
        id,
        bridge_id,
        title,
        status,
        payload_json,
        revision,
        sync_state,
        created_at,
        updated_at
      )
      VALUES (?, ?, ?, ?, ?, ?, 'local', ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        bridge_id = excluded.bridge_id,
        title = excluded.title,
        status = excluded.status,
        payload_json = excluded.payload_json,
        revision = excluded.revision,
        sync_state = 'local',
        updated_at = excluded.updated_at
    `,
    values: [
      id,
      payload.bridgeId || null,
      payload.title || id,
      payload.status || "draft",
      JSON.stringify(payload),
      revision,
      now,
      now,
    ],
    transaction: true,
    readonly: false,
  });

  await CapacitorSQLite.run({
    database: DB_NAME,
    statement: `
      INSERT INTO audit_log (
        inspection_id,
        event_type,
        event_json,
        created_at
      )
      VALUES (?, 'inspection_saved', ?, ?)
    `,
    values: [
      id,
      JSON.stringify({ revision }),
      now,
    ],
    transaction: true,
    readonly: false,
  });

  return {
    id,
    revision,
    savedAt: now,
  };
}

async function loadInspection(id) {
  await initialize();

  if (!nativePlatform()) {
    throw new Error(
      "loadInspection SQLite solo debe probarse dentro de Android/iOS."
    );
  }

  const result = await CapacitorSQLite.query({
    database: DB_NAME,
    statement: `
      SELECT *
      FROM inspections
      WHERE id = ?
      LIMIT 1
    `,
    values: [id],
    readonly: false,
  });

  const row = (result.values || []).find(
    (item) =>
      item &&
      typeof item === "object" &&
      item.id === id
  );

  if (!row) {
    return null;
  }

  let payload = {};

  try {
    payload = JSON.parse(row.payload_json || "{}");
  } catch {
    payload = {};
  }

  return {
    ...row,
    payload,
  };
}

async function health() {
  const base = await initialize();

  if (!nativePlatform()) {
    return base;
  }

  const result = await CapacitorSQLite.query({
    database: DB_NAME,
    statement: `
      SELECT COUNT(*) AS count
      FROM inspections
    `,
    values: [],
    readonly: false,
  });

  const row = (result.values || []).find(
    (item) =>
      item &&
      typeof item === "object" &&
      Object.prototype.hasOwnProperty.call(item, "count")
  );

  return {
    ...base,
    database: DB_NAME,
    inspectionCount: Number(row?.count || 0),
  };
}

async function selfTest() {
  if (!nativePlatform()) {
    return {
      passed: false,
      skipped: true,
      reason: "Ejecutar dentro de Android/iOS",
    };
  }

  const id = `FIELD-SELFTEST-${Date.now()}`;

  const original = {
    bridgeId: "99",
    title: "Prueba Offline Field",
    status: "test",
    probe: "SIPUCOL_OFFLINE_OK",
  };

  const saved = await saveInspection(id, original);
  const restored = await loadInspection(id);

  const passed =
    restored?.payload?.probe === "SIPUCOL_OFFLINE_OK" &&
    restored?.id === id;

  return {
    passed,
    id,
    saved,
    restored,
    health: await health(),
  };
}

const api = {
  initialize,
  health,
  selfTest,
  saveInspection,
  loadInspection,
};

Object.defineProperty(window, "sipucolField", {
  value: api,
  writable: false,
  enumerable: false,
  configurable: true,
});

initialize()
  .then((status) => {
    window.dispatchEvent(
      new CustomEvent("sipucol-field-ready", {
        detail: status,
      })
    );
  })
  .catch((error) => {
    console.error("[SIPUCOL FIELD ERROR]", error);

    window.dispatchEvent(
      new CustomEvent("sipucol-field-error", {
        detail: {
          message: error?.message || String(error),
        },
      })
    );
  });