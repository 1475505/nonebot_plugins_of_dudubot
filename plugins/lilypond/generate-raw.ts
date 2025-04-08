#!/usr/bin/env bun
import { $, ProcessOutput } from "bun";
import path from "node:path";
import { existsSync, unlinkSync, readFileSync } from "node:fs";

// 工具路径配置
const LILYPOND = "lilypond";
const GHOSTSCRIPT = "gs";
const IMAGEMAGICK_CONVERT = "convert";
const FLUIDSYNTH = "fluidsynth";

// 默认的 SOUNDFONT 路径
const DEFAULT_SOUNDFONT = "/usr/share/sounds/sf2/FluidR3_GM.sf2";

// 尝试从文件中读取 SOUNDFONT，若不存在则使用默认值
let SOUNDFONT = DEFAULT_SOUNDFONT;
const sf2FilePath = "/root/nb/dudubot/data/sf2.txt";
if (existsSync(sf2FilePath)) {
  try {
    const fileContent = readFileSync(sf2FilePath, "utf-8").trim();
    if (fileContent) {
      SOUNDFONT = fileContent;
    }
  } catch (err) {
    console.error(`无法从 ${sf2FilePath} 读取 SOUNDFONT：${err}`);
    // 继续使用默认的 SOUNDFONT
  }
}

// 使用 GhostScript 处理 PostScript 文件并生成 PNG 图片
async function runGhostScript() {
  const fileContent = await Bun.file("file.ps").text();
  const lines = fileContent.split("\n");
  for (const line of lines) {
    const match = line.match(/^%%DocumentMedia: [^ ]* ([\d.]+) ([\d.]+)/);
    if (match) {
      const [, width, height] = match;
      await $`${GHOSTSCRIPT} -q -dGraphicsAlphaBits=4 -dTextAlphaBits=4 -dDEVICEWIDTHPOINTS=${width} -dDEVICEHEIGHTPOINTS=${height} -dNOPAUSE -dSAFER -sDEVICE=png16m -sOutputFile=file-page%d.png -r101 file.ps -c quit`;
      return;
    }
  }
  throw new Error(`在 PostScript 文件中未找到 DocumentMedia。`);
}

// 裁剪生成的图片
async function trimImages() {
  let i = 1;
  const outputImages: string[] = [];
  while (true) {
    const filename = path.resolve(`file-page${i}.png`);
    if (!existsSync(filename)) {
      break;
    }
    await $`${IMAGEMAGICK_CONVERT} -trim -colorspace RGB ${filename} ${filename}`;
    outputImages.push(filename);
    i++;
  }
  return outputImages;
}

// 主函数
(async () => {
  try {
    // 获取用户输入的 LilyPond 源文件路径
    const rawSource = process.argv[2];
    if (!rawSource) {
      throw new Error("未指定输入文件。");
    }

    // 使用 LilyPond 生成 PostScript 和 MIDI 文件
    await $`${LILYPOND} -dmidiextension=midi --ps --header=texidoc --loglevel=ERROR -o file ${rawSource}`;

    // 使用 GhostScript 生成 PNG 图片
    await runGhostScript();

    // 裁剪图片
    const images = await trimImages();

    // 使用 FluidSynth 生成 WAV 音频文件
    await $`${FLUIDSYNTH} -T wav -F file.wav -r 44100 ${SOUNDFONT} file.midi`.quiet();

    // 输出结果
    process.stdout.write(JSON.stringify({ images, audio: path.resolve("file.wav") }));
  } catch (e) {
    if (e instanceof Error && 'stderr' in e) {
      process.stderr.write((e as any).stderr.toString());
    } else if (e instanceof Error) {
      process.stderr.write(e.message);
    } else {
      process.stderr.write(String(e));
    }
    process.exit(1);
  }
})();