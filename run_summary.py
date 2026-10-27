import sys
import glob
from analyzer import extract_hashtags, summarize_text

# 윈도우 콘솔 한글 인코딩 대응
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def analyze_file(file_path: str, num_lines: int = 3, num_tags: int = 5):
    print("=" * 60)
    print(f"📄 파일 분석: {file_path}")
    print("=" * 60)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return

    # 해시태그 및 요약 추출
    hashtags = extract_hashtags(text, top_n=num_tags)
    summary = summarize_text(text, num_lines=num_lines)

    print("\n🏷️ [주요 키워드 해시태그]")
    print(" ".join(hashtags))

    print(f"\n📝 [핵심 내용 요약 ({len(summary)}줄)]")
    for i, line in enumerate(summary, 1):
        print(f"{i}. {line}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 파일명이 인자로 전달된 경우
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        analyze_file(target_file, num_lines=lines)
    else:
        # 인자가 없으면 디렉토리 내 transcript_*.txt 파일 자동 탐색
        transcript_files = glob.glob("transcript_*.txt")
        if transcript_files:
            analyze_file(transcript_files[0], num_lines=3, num_tags=5)
        else:
            print("분석할 텍스트 파일(.txt)을 지정해 주세요. 예: py run_summary.py sample.txt")
