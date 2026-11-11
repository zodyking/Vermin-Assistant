import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "src/themes/home-assistant/home-assistant.d.ts",
      "src/themes/home-assistant/home-assistant.variants.d.ts",
      "src/themes/home-assistant/home-assistant.js",
    ],
  },
  js.configs.recommended,
  tseslint.configs.recommended,
);
