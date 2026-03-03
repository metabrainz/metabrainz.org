import {WebpackManifestPlugin} from "webpack-manifest-plugin";
import ForkTsCheckerWebpackPlugin from "fork-ts-checker-webpack-plugin";
import path from "path";
import StylelintPlugin from "stylelint-webpack-plugin";
import ESLintPlugin from "eslint-webpack-plugin";
import LessPluginCleanCSS from "less-plugin-clean-css";

export default function (env, argv) {
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
      extensions: ["js", "jsx", "ts", "tsx"],
      failOnError: isProd,
      cache: false,
    }),
  ];
  return {
    entry: {
      // Importing main.less file here so that it gets compiled.
      // Otherwise with a standalone entrypoint Webpack would generate a superfluous js file.
      // All the Less/CSS will be exported separately to a main.css file and not appear in the main module
      main: path.resolve(cssDir, "main.less"),
      admin: path.resolve(cssDir, "admin.css"),
      signupCommercial: path.resolve(jsDir, "src/forms/SignupCommercial.tsx"),
      signupNonCommercial: path.resolve(
        jsDir,
        "src/forms/SignupNonCommercial.tsx"
      ),
      createApplication: path.resolve(jsDir, "src/forms/CreateApplication.tsx"),
      deleteApplication: path.resolve(jsDir, "src/forms/DeleteApplication.tsx"),
      oauthPrompt: path.resolve(jsDir, "src/forms/OAuthPrompt.tsx"),
      applications: path.resolve(jsDir, "src/Applications.tsx"),
      oauthError: path.resolve(jsDir, "src/OAuthError.tsx"),
      signupUser: path.resolve(jsDir, "src/forms/SignupUser.tsx"),
      loginUser: path.resolve(jsDir, "src/forms/LoginUser.tsx"),
      lostPassword: path.resolve(jsDir, "src/forms/LostPassword.tsx"),
      lostUsername: path.resolve(jsDir, "src/forms/LostUsername.tsx"),
      resetPassword: path.resolve(jsDir, "src/forms/ResetPassword.tsx"),
      profileEdit: path.resolve(jsDir, "src/forms/ProfileEdit.tsx"),
      profile: path.resolve(jsDir, "src/Profile.tsx"),
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
        {
          test: /\.css$/i,
          type: "asset/resource",
          generator: {
            filename: isProd ? "[name].[contenthash].css" : "[name].css",
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
}
