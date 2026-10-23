import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { safeCitationHref } from "../src/lib/citation-url.ts";

interface CitationFixture {
  id: string;
  input: string;
  expected: string | null;
}

const fixtures = JSON.parse(
  readFileSync(new URL("../../shared/citation_url_fixtures.json", import.meta.url), "utf8"),
) as CitationFixture[];

for (const fixture of fixtures) {
  assert.equal(safeCitationHref(fixture.input), fixture.expected, fixture.id);
}

process.stdout.write(`Validated ${fixtures.length} shared citation URL fixtures.\n`);
