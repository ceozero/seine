import { LOCALES, type Locale } from './locales';
import en from './messages/en.json';

// Interface strings live in messages/<locale>.json, one file per locale with the same keys as
// en.json. Keys ending in "Html" contain inline markup and are rendered with set:html.
// "{name}" placeholders are filled by the function useTranslations returns.
export type UiKey = keyof typeof en;

const files = import.meta.glob<Record<UiKey, string>>('./messages/*.json', { eager: true, import: 'default' });
const CATALOGS = Object.fromEntries(
    Object.entries(files).map(([path, catalog]) => [path.slice('./messages/'.length, -'.json'.length), catalog]),
) as Record<Locale, Record<UiKey, string>>;

// `astro build` doesn't type-check, so enforce complete catalogs here; a gap fails the build.
for (const { code } of LOCALES) {
    const catalog = CATALOGS[code];
    if (!catalog) throw new Error(`missing src/i18n/messages/${code}.json`);
    const missing = Object.keys(en).filter((k) => !catalog[k as UiKey]);
    const extra = Object.keys(catalog).filter((k) => !(k in en));
    if (missing.length || extra.length) {
        throw new Error(`messages/${code}.json: missing [${missing.join(', ')}] extra [${extra.join(', ')}]`);
    }
}

export function useTranslations(locale: Locale) {
    const catalog = CATALOGS[locale];
    return (key: UiKey, vars: Record<string, string | number> = {}) =>
        catalog[key].replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? `{${name}}`));
}
