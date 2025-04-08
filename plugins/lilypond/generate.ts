#!/usr/bin/env bun
import { $, ShellError } from "bun";
import path from "node:path";
import { existsSync } from "node:fs";

const LILYPOND = "lilypond";
const GHOSTSCRIPT = "gs";
const IMAGEMAGICK_CONVERT = "convert";
const FLUIDSYNTH = "fluidsynth";

const SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2";

// const tempdir = await fs.mkdtemp("lilypond-");
// process.chdir(tempdir);

function preprocessSource(source: string) {
  return String.raw`
\header {
	tagline = ##f
}
\score {
  ${source}

\layout {}
  \midi {
    \context { \Score tempoWholesPerMinute = #(ly:make-moment 100 4) }
  }
}
\paper {
  indent = 0\mm
}`;
}

export async function runGhostScript() {
  const fileContent = await Bun.file("file.ps").text();
  const lines = fileContent.split("\n");
  for (const line of lines) {
    const match = line.match(/^%%DocumentMedia: [^ ]* ([\d.]+) ([\d.]+)/);
    if (match) {
      const [_, width, height] = match;
      await $`${GHOSTSCRIPT} -q -dGraphicsAlphaBits=4 -dTextAlphaBits=4 -dDEVICEWIDTHPOINTS=${width} -dDEVICEHEIGHTPOINTS=${height} -dNOPAUSE -dSAFER -sDEVICE=png16m -sOutputFile=file-page%d.png -r101 file.ps -c quit`;
      return;
    }
  }
  throw new Error(`No DocumentMedia found in PostScript file`);
}

async function trimImages() {
  let i = 1;
  const outputImages: string[] = [];
  while (true) {
    const filename = path.resolve(`file-page${i}.png`);
    if (!existsSync(filename)) {
      break;
    }
    await $`${IMAGEMAGICK_CONVERT} -trim -colorspace RGB file-page${i}.png trimmed.png`;
    await $`mv trimmed.png file-page${i}.png`;
    outputImages.push(filename);
    i++;
  }
  return outputImages;
}

try {
  await Bun.write("file.ly", preprocessSource(process.argv[2]));
  await $`${LILYPOND} -dmidiextension=midi --ps --header=texidoc --loglevel=ERROR file.ly`;
  await runGhostScript();
  const images = await trimImages();
  await $`${FLUIDSYNTH} -T wav -F file.wav -r 44100 ${SOUNDFONT} file.midi`.quiet();

  process.stdout.write(JSON.stringify({ images, audio: path.resolve("file.wav") }));
} catch (e) {
  if ("stderr" in e) {
    // process.stderr.write(e.stderr);
  } else {
    process.stderr.write(e.toString());
  }
  process.exit(1);
}
