/**
 * Export utilities for query results.
 *
 * Two export strategies are supported:
 *
 * 1. Client-side export (`exportResultClient`) -- serialises the
 *    already-loaded `QueryResult` in the browser and triggers a download.
 *    This is instant for results already on screen.
 * 2. Server-side export (`exportResultServer`) -- calls the backend
 *    `/api/v1/dbs/{name}/export` endpoint which re-executes the SQL and
 *    streams back a CSV/JSON file. This is what the AI Agent / one-click
 *    automation uses, because a single HTTP call does both "run query" and
 *    "produce file".
 */
import { apiClient } from "./api";
import type { QueryResult } from "../types/query";

export type ExportFormat = "csv" | "json";

/** Trigger a browser download for a Blob payload. */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/** Build a timestamped filename such as `mydb_query_20260422T103000.csv`. */
export function buildExportFilename(
  databaseName: string,
  format: ExportFormat
): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const stamp =
    `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}` +
    `T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}Z`;
  const safe = databaseName.replace(/[^A-Za-z0-9_-]/g, "_");
  return `${safe}_query_${stamp}.${format}`;
}

/** Escape a single CSV cell following RFC 4180. */
function escapeCsvCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

/** Serialise a QueryResult to CSV text (UTF-8, with BOM for Excel). */
export function resultToCsv(result: QueryResult): string {
  const headers = result.columns.map((c) => c.name);
  const lines = [headers.map(escapeCsvCell).join(",")];
  for (const row of result.rows) {
    lines.push(headers.map((h) => escapeCsvCell(row[h])).join(","));
  }
  return lines.join("\r\n");
}

/** Serialise a QueryResult to a pretty-printed JSON string (with metadata). */
export function resultToJson(result: QueryResult, databaseName?: string): string {
  const payload = {
    metadata: {
      database: databaseName ?? null,
      generatedAt: new Date().toISOString(),
      rowCount: result.rowCount,
      executionTimeMs: result.executionTimeMs,
      sql: result.sql,
      columns: result.columns,
    },
    rows: result.rows,
  };
  return JSON.stringify(payload, null, 2);
}

/**
 * Export an in-memory query result entirely on the client side.
 * Adds the UTF-8 BOM for CSV so that Excel opens Unicode correctly.
 */
export function exportResultClient(
  result: QueryResult,
  format: ExportFormat,
  databaseName: string
): void {
  const filename = buildExportFilename(databaseName, format);
  if (format === "csv") {
    // Prepend BOM so Excel detects UTF-8.
    const blob = new Blob(["\uFEFF" + resultToCsv(result)], {
      type: "text/csv;charset=utf-8;",
    });
    downloadBlob(blob, filename);
  } else {
    const blob = new Blob([resultToJson(result, databaseName)], {
      type: "application/json;charset=utf-8;",
    });
    downloadBlob(blob, filename);
  }
}

/**
 * Server-side one-click export. The backend executes the SQL and streams
 * back a file. Useful for AI Agent automation where only SQL text is known.
 *
 * The `onDownloadProgress` callback lets the UI show progress for large
 * result sets.
 */
export async function exportResultServer(
  databaseName: string,
  sql: string,
  format: ExportFormat,
  onDownloadProgress?: (event: ProgressEvent) => void
): Promise<{ filename: string; bytes: number }> {
  const response = await apiClient.post(
    `/api/v1/dbs/${encodeURIComponent(databaseName)}/export`,
    { sql, format },
    { responseType: "blob", onDownloadProgress }
  );

  // Prefer the server-suggested filename from Content-Disposition when present.
  const disposition = response.headers["content-disposition"] as string | undefined;
  let filename = buildExportFilename(databaseName, format);
  if (disposition) {
    const match = /filename="?([^"]+)"?/.exec(disposition);
    if (match && match[1]) filename = match[1];
  }

  const blob = new Blob([response.data], {
    type: format === "csv" ? "text/csv;charset=utf-8" : "application/json;charset=utf-8",
  });
  downloadBlob(blob, filename);
  return { filename, bytes: blob.size };
}
