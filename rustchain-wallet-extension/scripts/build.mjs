import { build } from "esbuild";
import { copyFileSync, mkdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const dist = join(root, "dist");
rmSync(dist, { recursive: true, force: true });
mkdirSync(dist, { recursive: true });

await build({
  entryPoints: ["src/popup.js"],
  bundle: true,
  format: "esm",
  outfile: "dist/popup.js",
  target: "chrome120",
  minify: true,
});

for (const file of ["manifest.json", "src/popup.html", "src/popup.css"]) {
  copyFileSync(join(root, file), join(dist, file.replace("src/", "")));
}

console.log("Built dist/");
