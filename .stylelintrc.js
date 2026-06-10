module.exports = {
  extends: "stylelint-config-recommended-less",
  customSyntax: "postcss-less",
  plugins: ["stylelint-prettier"],
  rules: {
    "prettier/prettier": true,
    "at-rule-no-unknown": null,
    "no-descending-specificity": null,
    "function-calc-no-unspaced-operator": null,
  },
  ignoreFiles: [
    "**/static/css/theme/bootstrap/*",
    "**/static/css/theme/bootstrap/mixins/*",
  ],
}
