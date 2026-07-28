#!/usr/bin/env node
/**
 * Fail when generated OpenAPI types drift from modules/web/openapi/openapi.json.
 * Writes to a temp file and diffs against src/types/api.d.ts (PPT-065).
 */
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const artifact = join(root, "openapi", "openapi.json");
const committed = join(root, "src", "types", "api.d.ts");
const tempDir = mkdtempSync(join(tmpdir(), "papita-openapi-"));
const generated = join(tempDir, "api.d.ts");

try {
  const result = spawnSync("pnpm", ["exec", "openapi-typescript", artifact, "-o", generated], {
    cwd: root,
    encoding: "utf8",
  });
  if (result.status !== 0) {
    process.stderr.write(result.stderr || result.stdout || "openapi-typescript failed\n");
    process.exit(result.status ?? 1);
  }

  const expected = readFileSync(generated, "utf8");
  let actual;
  try {
    actual = readFileSync(committed, "utf8");
  } catch {
    process.stderr.write(`ERROR: missing ${committed}\nRun: make generate-types\n`);
    process.exit(1);
  }

  if (actual !== expected) {
    process.stderr.write(
      `ERROR: OpenAPI TypeScript types drift (${committed}).\n` +
        "Fix: make sync-openapi && make generate-types\n",
    );
    // Help local debugging without dumping huge files to CI logs by default.
    if (process.env.OPENAPI_TYPES_DIFF === "1") {
      writeFileSync(join(tempDir, "expected.d.ts"), expected);
      const diff = spawnSync("diff", ["-u", committed, generated], { encoding: "utf8" });
      process.stderr.write(diff.stdout || diff.stderr || "");
    }
    process.exit(1);
  }

  process.stdout.write(`OK: OpenAPI types in sync (${committed})\n`);
} finally {
  rmSync(tempDir, { recursive: true, force: true });
}
