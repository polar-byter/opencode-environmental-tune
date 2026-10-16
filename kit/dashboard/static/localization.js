/* English source keys; substitution values are data and are never translated. */
(function (scope) {
  'use strict';
  function choose(values, fallback = 'en') {
    for (const value of values || []) {
      const language = String(value || '').toLowerCase().split(/[-_.@]/)[0];
      if (language === 'en' || language === 'ru') return language;
    }
    return fallback;
  }
  function create(catalog = {}, language = 'en') {
    const reverse = new Map(Object.entries(catalog).map(([source, translated]) => [translated, source]));
    const state = {
      language: choose([language]),
      set(value) { this.language = choose([value]); },
      get locale() { return this.language === 'ru' ? 'ru-RU' : 'en-US'; },
      text(key) {
        if (this.language === 'ru') return catalog[key] ?? key;
        return reverse.get(key) ?? key;
      },
      template(parts, ...values) {
        const key = parts.reduce((all, part, index) => all + (index ? '{' + (index - 1) + '}' : '') + part, '');
        return this.text(key).replace(/\{(\d+)\}/g, (match, index) => index < values.length ? String(values[index]) : match);
      },
      apply(document) {
        document.documentElement.lang = this.language;
        for (const node of document.querySelectorAll('[data-i18n]')) node.textContent = this.text(node.dataset.i18n);
        for (const attribute of ['title', 'aria-label']) {
          for (const node of document.querySelectorAll('[data-i18n-' + attribute + ']')) {
            node.setAttribute(attribute, this.text(node.getAttribute('data-i18n-' + attribute)));
          }
        }
      }
    };
    return state;
  }
  scope.KitLocalization = {choose, create};
  if (typeof module !== 'undefined') module.exports = scope.KitLocalization;
})(globalThis);
