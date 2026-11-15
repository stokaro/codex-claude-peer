import fs from "node:fs";
import path from "node:path";
import { JSDOM } from "jsdom";

const { window } = new JSDOM("<!doctype html><html><body></body></html>");
globalThis.window = window;
globalThis.document = window.document;
const { default: mermaid } = await import("mermaid");

function markdownFiles(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    if (entry.name === ".git" || entry.name === "node_modules") return [];
    const item = path.join(directory, entry.name);
    if (entry.isDirectory()) return markdownFiles(item);
    return entry.isFile() && item.endsWith(".md") ? [item] : [];
  });
}

function diagrams(markdown) {
  return [...markdown.matchAll(/^```mermaid\s*\n([\s\S]*?)^```/gm)].map(match => match[1]);
}

async function check(source, label) {
  try {
    await mermaid.parse(source);
    process.stdout.write(`ok ${label}\n`);
  } catch (error) {
    throw new Error(`${label}: ${error.message}`, { cause: error });
  }
}

if (process.argv.includes("--selftest")) {
  await check("sequenceDiagram\n    A->>B: accepted, pending", "valid sequence");
  let rejected = false;
  try {
    await mermaid.parse("sequenceDiagram\n    A->>B: accepted; pending\n    B->>A: reply");
  } catch {
    rejected = true;
  }
  if (!rejected) throw new Error("selftest failed: Mermaid accepted the broken sequence diagram");
  process.stdout.write("selftest passed\n");
} else {
  let count = 0;
  for (const file of markdownFiles(".")) {
    for (const [index, source] of diagrams(fs.readFileSync(file, "utf8")).entries()) {
      count++;
      await check(source, `${file} diagram ${index + 1}`);
    }
  }
  if (count === 0) throw new Error("No Mermaid diagrams found");
  process.stdout.write(`${count} Mermaid diagrams valid\n`);
}
