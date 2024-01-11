const path = require("path");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const ForkTsCheckerWebpackPlugin = require("fork-ts-checker-webpack-plugin");
const LessPluginCleanCSS = require("less-plugin-clean-css");
const StylelintPlugin = require("stylelint-webpack-plugin");
const ESLintPlugin = require("eslint-webpack-plugin");

module.exports = function (env, argv) {
  const isProd = argv.mode === "production";
  const baseDir = "./frontend";
  const jsDir = path.join(baseDir, "js");
  const distDir = path.join(baseDir, "dist");
  const cssDir = path.join(baseDir, "css");

  const babelExcludeLibrariesRegexp = new RegExp("node_modules/.*", "");

  const plugins = [
    new WebpackManifestPlugin(),
    new ForkTsCheckerWebpackPlugin({
      typescript: {
        diagnosticOptions: {
          semantic: true,
          syntactic: true,
        },
        mode: "write-references",
        memoryLimit: 4096,
      },
    }),
    new StylelintPlugin({
      configFile: ".stylelintrc.js",
      failOnError: isProd,
      files: "**/static/css/**/*.less",
      fix: !isProd,
      threads: true,
    }),
    new ESLintPlugin({
      files: path.join(jsDir, "src/**/*.{ts,tsx,js,jsx}"),
      fix: !isProd,
    }),
  ];
  return {
    entry: {
      // Importing main.less file here so that it gets compiled.
      // Otherwise with a standalone entrypoint Webpack would generate a superfluous js file.
      // All the Less/CSS will be exported separately to a main.css file and not appear in the main module
      main: [
        path.resolve(jsDir, "src/main.tsx"),
        path.resolve(cssDir, "main.less"),
      ],
      signupCommercial: path.resolve(jsDir, "src/forms/SignupCommercial.tsx"),
      signupNonCommercial: path.resolve(jsDir, "src/forms/SignupNonCommercial.tsx"),
      profileEdit: path.resolve(jsDir, "src/forms/ProfileEdit.tsx")
    },
    output: {
      filename: isProd ? "[name].[contenthash].js" : "[name].js",
      path: path.resolve(distDir),
      // This is for the manifest file used by the server. Files end up in /static folder
      publicPath: "/static/dist/",
      clean: true, // Clean the output directory before emit.
    },
    devtool: isProd ? "source-map" : "eval-source-map",
    module: {
      rules: [
        {
          test: /\.(js|ts)x?$/,
          // exclude third-party libraries from ES5 transpilation
          exclude: babelExcludeLibrariesRegexp,
          // Don't specify the babel configuration here
          // Configuration can be found in ./babel.config.js
          use: "babel-loader",
        },
        {
          test: /\.less$/i,
          type: "asset/resource",
          loader: "less-loader",
          generator: {
            filename: isProd ? "[name].[contenthash].css" : "[name].css",
          },
          options: {
            lessOptions: {
              math: "always",
              plugins: [new LessPluginCleanCSS({ advanced: true })],
            },
          },
        },
      ],
    },
    resolve: {
      modules: [
        path.resolve("./node_modules"),
        "/code/node_modules",
        path.resolve(baseDir, "node_modules"),
      ],
      extensions: [".ts", ".tsx", ".js", ".jsx", ".json"],
    },
    plugins,
  };
};
