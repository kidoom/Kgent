const fs = require("fs/promises");
const path = require("path");

const root = path.resolve(__dirname, "..");
const electronDist = path.join(root, "node_modules", "electron", "dist");
const rendererDist = path.join(root, "dist");
const releaseRoot = path.join(root, "release");
const appName = "Kgent";
const outDir = path.join(releaseRoot, `${appName}-win32-x64`);
const appDir = path.join(outDir, "resources", "app");

async function assertExists(target, label) {
  try {
    await fs.access(target);
  } catch {
    throw new Error(`${label} not found: ${target}`);
  }
}

async function copyAppFiles() {
  await fs.mkdir(appDir, { recursive: true });
  await fs.cp(path.join(root, "electron"), path.join(appDir, "electron"), {
    recursive: true,
  });
  await fs.cp(rendererDist, path.join(appDir, "dist"), { recursive: true });
  await fs.writeFile(
    path.join(appDir, "package.json"),
    JSON.stringify(
      {
        name: "kgent-desktop",
        productName: appName,
        version: "0.1.0",
        main: "electron/main.cjs",
      },
      null,
      2,
    ),
  );
}

async function main() {
  await assertExists(path.join(electronDist, "electron.exe"), "Electron runtime");
  await assertExists(path.join(rendererDist, "index.html"), "Renderer build");

  await fs.rm(outDir, { recursive: true, force: true });
  await fs.mkdir(releaseRoot, { recursive: true });
  await fs.cp(electronDist, outDir, { recursive: true });
  await fs.rename(path.join(outDir, "electron.exe"), path.join(outDir, `${appName}.exe`));
  await copyAppFiles();

  console.log(`Packaged ${appName} desktop client: ${outDir}`);
  console.log("Start the backend first, then run Kgent.exe.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
