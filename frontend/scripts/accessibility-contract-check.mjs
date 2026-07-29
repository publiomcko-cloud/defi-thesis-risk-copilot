import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = fileURLToPath(new URL("..", import.meta.url));
const appRoot = join(frontendRoot, "src", "app");
const delegatedPages = new Map([
  ["admin/credentials/page.tsx", "admin/provider-credentials/page.tsx"],
  ["reports/[reportId]/page.tsx", "reports/[reportId]/report-viewer.tsx"]
]);

const pages = await findPages(appRoot);
assert(pages.length > 0, "the application must contain route pages");
for (const page of pages) {
  const relativePage = relative(appRoot, page).replaceAll("\\", "/");
  const source = await readFile(page, "utf8");
  if (source.includes("<main") && source.includes("<h1")) {
    continue;
  }
  const delegate = delegatedPages.get(relativePage);
  assert(delegate, `${relativePage} must render a main landmark and h1 or declare its semantic delegate`);
  const delegatedSource = await readFile(join(appRoot, delegate), "utf8");
  assert(delegatedSource.includes("<main") && delegatedSource.includes("<h1"), `${delegate} must provide the delegated main landmark and h1`);
}

const header = await readFile(join(frontendRoot, "src", "components", "SiteHeader.tsx"), "utf8");
assert(header.includes('aria-label="Main navigation"'), "site navigation requires an accessible name");

const stylesheet = await readFile(join(appRoot, "v1.css"), "utf8");
assert(stylesheet.includes(":focus-visible"), "interactive controls require visible keyboard focus styling");

console.log(`Accessibility contract check passed for ${pages.length} route pages.`);

async function findPages(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const pages = [];
  for (const entry of entries) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      pages.push(...await findPages(path));
    } else if (entry.name === "page.tsx") {
      pages.push(path);
    }
  }
  return pages;
}
