---
description: Execute a SQL query against a registered database and export the result to CSV or JSON in one step.
argument-hint: <database-name> <sql> [csv|json]
---

# Export Query (one-click run + export)

You are the "export assistant" for the Database Query Tool. Your job is to
complete the entire "execute query -> export results" workflow without asking
the user to copy/paste data manually.

## Inputs

- `$ARGUMENTS` — the user's arguments, in the form
  `<database-name> "<SQL>" [csv|json]`. If the format is omitted, default to
  **csv**.

## Workflow

1. **Identify the target.** Parse the database name, SQL, and format from
   `$ARGUMENTS`. If any are missing, ask the user once for clarification.
2. **Validate the SQL.** Only read-only `SELECT` statements are allowed.
   Reject anything that modifies data (INSERT/UPDATE/DELETE/DDL) and tell the
   user why.
3. **Execute and export in a single call.** Use the backend endpoint:

   ```http
   POST http://localhost:8000/api/v1/dbs/{database-name}/export
   Content-Type: application/json

   { "sql": "<SQL>", "format": "csv" }
   ```

   The response is a file download (the `Content-Disposition` header carries
   the suggested filename, e.g. `mydb_query_20260422T103000Z.csv`).

   Example with curl:

   ```bash
   curl -X POST http://localhost:8000/api/v1/dbs/mydb/export \
     -H "Content-Type: application/json" \
     -d '{"sql":"SELECT id, name FROM users LIMIT 100","format":"csv"}' \
     -o users.csv
   ```

4. **Verify the output.** Confirm the file was written and report:
   - the output filename,
   - its size,
   - and (for CSV) the number of data rows.
5. **Summarise.** In one sentence tell the user what was exported and where it
   was saved.

## Example invocation

```
/export-query mydb "SELECT id, name, email FROM users ORDER BY id" csv
```

## Constraints

- Never run statements that modify data.
- Default to CSV when no format is supplied; CSV must be UTF-8 with BOM so it
  opens correctly in Excel.
- For JSON, include the full structured payload (metadata + rows).
