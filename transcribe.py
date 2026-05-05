"""
transcribe.py — 音檔逐字稿產生器（本地 Whisper，免費離線）
用法：python transcribe.py <音檔路徑> [--date YYYY-MM-DD] [--model medium]
輸出：minutes/逐字稿_YYYY-MM-DD.txt

安裝：pip install openai-whisper
      winget install ffmpeg
"""

import argparse
import sys
from pathlib import Path
from datetime import date


def transcribe(audio_path: Path, output_date: str, model_name: str) -> Path:
    try:
        import whisper
    except ImportError:
        print("請先安裝套件：pip install openai-whisper")
        sys.exit(1)

    if not audio_path.exists():
        print(f"找不到檔案：{audio_path}")
        sys.exit(1)

    print(f"載入模型 {model_name}（第一次會自動下載）...")
    model = whisper.load_model(model_name)

    print(f"正在辨識：{audio_path.name} ...")
    result = model.transcribe(str(audio_path), language="zh", verbose=False)

    output_dir = Path(__file__).parent / "minutes"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"逐字稿_{output_date}.txt"

    with open(output_path, "w", encoding="utf-8") as out:
        out.write(f"# 逐字稿 {output_date}\n")
        out.write(f"# 來源音檔：{audio_path.name}\n\n")
        for seg in result["segments"]:
            start = _fmt_time(seg["start"])
            out.write(f"[{start}] {seg['text'].strip()}\n")

    print(f"完成，輸出至：{output_path}")
    return output_path


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(description="音檔逐字稿產生器")
    parser.add_argument("audio", help="音檔路徑（mp3 / m4a / wav / mp4）")
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="會議日期 YYYY-MM-DD（預設今天）",
    )
    parser.add_argument(
        "--model",
        default="medium",
        choices=["tiny", "base", "small", "medium", "large", "large-v3"],
        help="Whisper 模型大小（預設 medium）",
    )
    args = parser.parse_args()

    transcribe(Path(args.audio), args.date, args.model)


if __name__ == "__main__":
    main()
