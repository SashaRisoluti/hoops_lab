import { readFileSync } from "node:fs";

/** Parse a JSON fixture from `tests/fixtures/` (trimmed real ESPN payloads). */
export function fixture(name: string): unknown {
  return JSON.parse(readFileSync(new URL(`./fixtures/${name}`, import.meta.url), "utf8"));
}
