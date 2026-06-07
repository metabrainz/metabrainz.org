import i18next from "i18next";
import { initReactI18next } from "react-i18next";

const DEFAULT_LOCALE = "en";

function loadCatalog(locale: string) {
  if (locale === DEFAULT_LOCALE) {
    return;
  }

  fetch(`/static/locales/${locale}/messages.json`)
    .then((response) => {
      if (!response.ok) {
        return {};
      }
      return response.json();
    })
    .then((messages) => {
      i18next.addResourceBundle(locale, "translation", messages, true, true);
      i18next.changeLanguage(locale);
    });
}

export function initI18n(globalProps: Record<string, any>) {
  const { locale } = globalProps;

  if (i18next.isInitialized) {
    i18next.changeLanguage(locale);
    loadCatalog(locale);
    return;
  }

  i18next.use(initReactI18next).init({
    fallbackLng: DEFAULT_LOCALE,
    interpolation: {
      escapeValue: false,
    },
    keySeparator: false,
    lng: locale,
    nsSeparator: false,
  });
  loadCatalog(locale);
}
