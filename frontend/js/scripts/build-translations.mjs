// Convert the gettext .po catalogs into the flat JSON catalogs that the React
// frontend (i18next) loads at runtime from /static/locales/<locale>/messages.json.
//
// Source:  metabrainz/translations/<locale>/LC_MESSAGES/messages.po
// Target:  frontend/locales/<locale>/messages.json
//
// Untranslated entries are skipped so that i18next falls back to the English
// key (which is the source string) instead of rendering an empty string.

import { readdir, readFile, mkdir, writeFile } from "fs/promises";
import path from "path";
import { gettextToI18next } from "i18next-conv";

const TRANSLATIONS_DIR = "metabrainz/translations";
const OUTPUT_DIR = "frontend/locales";

async function readCatalog(locale) {
  const poPath = path.join(TRANSLATIONS_DIR, locale, "LC_MESSAGES", "messages.po");
  try {
    return await readFile(poPath);
  } catch {
    // Locale directory without a catalog (e.g. an empty placeholder); skip it.
    return null;
  }
}

async function build() {
  const entries = await readdir(TRANSLATIONS_DIR, { withFileTypes: true });
  const locales = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name);

  let count = 0;
  for (const locale of locales) {
    const po = await readCatalog(locale);
    if (!po) {
      continue;
    }
    const json = await gettextToI18next(locale, po, { skipUntranslated: true });
    const localeDir = path.join(OUTPUT_DIR, locale);
    await mkdir(localeDir, { recursive: true });
    await writeFile(path.join(localeDir, "messages.json"), json);
    count += 1;
  }

  // eslint-disable-next-line no-console
  console.log(`Generated ${count} JSON translation catalogs in ${OUTPUT_DIR}.`);
}

build().catch((error) => {
  // eslint-disable-next-line no-console
  console.error(error);
  process.exit(1);
});
