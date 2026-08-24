import { Capacitor } from "@capacitor/core";
import { CapacitorSQLite } from "@capacitor-community/sqlite";
import { Network } from "@capacitor/network";

const TEST_DB = "sipucol_field_native_smoke";

async function cleanupTestDatabase() {
  try {
    await CapacitorSQLite.close({
      database: TEST_DB,
      readonly: false,
    });
  } catch {
    // Puede no estar abierta.
  }

  try {
    await CapacitorSQLite.closeConnection({
      database: TEST_DB,
      readonly: false,
    });
  } catch {
    // Puede no existir conexión.
  }

  try {
    await CapacitorSQLite.deleteDatabase({
      database: TEST_DB,
      readonly: false,
    });
  } catch {
    // Puede no existir todavía.
  }
}

export async function runNativeSQLiteSmokeTest() {
  const startedAt = new Date().toISOString();

  if (!Capacitor.isNativePlatform()) {
    return {
      passed: false,
      skipped: true,
      reason: "not-native",
      platform: Capacitor.getPlatform(),
      startedAt,
    };
  }

  const network = await Network.getStatus();

  await cleanupTestDatabase();

  try {
    await CapacitorSQLite.createConnection({
      database: TEST_DB,
      encrypted: false,
      mode: "no-encryption",
      version: 1,
      readonly: false,
    });

    await CapacitorSQLite.open({
      database: TEST_DB,
      readonly: false,
    });

    await CapacitorSQLite.execute({
      database: TEST_DB,
      statements: `
        CREATE TABLE IF NOT EXISTS native_probe (
          id INTEGER PRIMARY KEY NOT NULL,
          marker TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
      `,
      transaction: true,
      readonly: false,
    });

    const marker =
      "SIPUCOL_NATIVE_SQLITE_" +
      Date.now();

    await CapacitorSQLite.run({
      database: TEST_DB,
      statement: `
        INSERT INTO native_probe (
          id,
          marker,
          created_at
        )
        VALUES (?, ?, ?)
      `,
      values: [
        1,
        marker,
        new Date().toISOString(),
      ],
      transaction: true,
      readonly: false,
    });

    const query = await CapacitorSQLite.query({
      database: TEST_DB,
      statement: `
        SELECT
          id,
          marker,
          created_at
        FROM native_probe
        WHERE id = ?
        LIMIT 1
      `,
      values: [1],
      readonly: false,
    });

    const rows = Array.isArray(query?.values)
      ? query.values
      : [];

    const row = rows.find(
      (item) =>
        item &&
        typeof item === "object" &&
        Number(item.id) === 1
    );

    const passed =
      Boolean(row) &&
      row.marker === marker;

    const result = {
      passed,
      platform: Capacitor.getPlatform(),
      native: true,
      sqlite: passed ? "ok" : "mismatch",
      connected: Boolean(network.connected),
      connectionType:
        network.connectionType ||
        "unknown",
      markerExpected: marker,
      markerRestored:
        row?.marker ||
        null,
      startedAt,
      finishedAt:
        new Date().toISOString(),
    };

    console.log(
      "[FIELD_NATIVE_SMOKE]",
      JSON.stringify(result)
    );

    return result;
  } catch (error) {
    const result = {
      passed: false,
      platform: Capacitor.getPlatform(),
      native: true,
      sqlite: "error",
      connected: Boolean(network.connected),
      connectionType:
        network.connectionType ||
        "unknown",
      error:
        error?.message ||
        String(error),
      startedAt,
      finishedAt:
        new Date().toISOString(),
    };

    console.error(
      "[FIELD_NATIVE_SMOKE_ERROR]",
      JSON.stringify(result)
    );

    return result;
  } finally {
    await cleanupTestDatabase();
  }
}