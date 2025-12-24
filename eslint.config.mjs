import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import jsxA11y from "eslint-plugin-jsx-a11y";
import {importX} from "eslint-plugin-import-x";
import prettier from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  {
    ignores: ["node_modules/**", "frontend/dist/**", "**/*.d.ts"],
  },

  js.configs.recommended,

  ...tseslint.configs.recommended,

  react.configs.flat.recommended,
  react.configs.flat["jsx-runtime"],

  {
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: reactHooks.configs.recommended.rules,
  },

  jsxA11y.flatConfigs.recommended,

  importX.flatConfigs.recommended,
  importX.flatConfigs.typescript,

  prettier,

  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2018,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.es2015,
        Atomics: "readonly",
        SharedArrayBuffer: "readonly",
      },
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    settings: {
      react: {
        version: "detect",
      },
      "import-x/resolver": {
        typescript: {
          alwaysTryTypes: true,
        },
        node: {
          extensions: [".js", ".jsx", ".ts", ".tsx"],
        },
      },
    },
    rules: {
      "react/prop-types": "off",
      "react/jsx-filename-extension": "off",
      "react/jsx-props-no-spreading": "off",
      "react/no-did-update-set-state": "off",
      "react/static-property-placement": "off",
      "react/no-unused-class-component-methods": "off",
      "no-unused-vars": "off",
      camelcase: "off",
      "class-methods-use-this": "off",
      "default-param-last": "off",

      "lines-between-class-members": [
        "error",
        "always",
        { exceptAfterSingleLine: true },
      ],
      "jsx-a11y/label-has-associated-control": ["error", { assert: "either" }],

      "import-x/extensions": "off",
      "import-x/prefer-default-export": "off",
      "import-x/no-named-as-default-member": "off",
      "import-x/default": "off",
    },
  },
  {
    files: ["**/*.ts", "**/*.tsx"],
    rules: {
      "no-undef": "off",
      "no-use-before-define": "off",
      "@typescript-eslint/no-use-before-define": "warn",
      "react/require-default-props": "off",
      "no-shadow": "off",
      "@typescript-eslint/no-shadow": "error",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^React$" },
      ],
      "@typescript-eslint/no-explicit-any": "off",
    },
  }
);
