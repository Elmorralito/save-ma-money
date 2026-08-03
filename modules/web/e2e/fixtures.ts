import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export type E2ESeed = {
  apiBase: string;
  email: string;
  password: string;
  username: string;
  ownerId: string;
  accountIds: { checking: string; savings: string };
  accountNames: { checking: string; savings: string };
  categoryIds: { expense: string; income: string };
  categoryNames: { expense: string; income: string };
  baselineTxnId: string;
  baselineDescription: string;
  namePrefix: string;
  seedId: string;
};

const e2eDir = path.dirname(fileURLToPath(import.meta.url));
export const SEED_PATH = path.join(e2eDir, ".auth", "seed.json");

/** Load PPT-061 seed artifact written by `make web-e2e-seed`. */
export function loadSeed(): E2ESeed {
  const raw = readFileSync(SEED_PATH, "utf8");
  return JSON.parse(raw) as E2ESeed;
}
