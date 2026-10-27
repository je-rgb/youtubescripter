import re
import urllib.parse
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    IpBlocked,
)


def extract_video_id(url_or_id: str) -> str:
    """유튜브 URL 또는 영상 ID에서 11자리 비디오 ID를 추출합니다."""
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        parsed = urllib.parse.urlparse(url_or_id)
        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/")
        query = urllib.parse.parse_qs(parsed.query)
        if "v" in query:
            return query["v"][0]

    # 이미 ID 형태(11자 영숫자/특수기호)인 경우 그대로 반환
    match = re.search(r"([a-zA-Z0-9_-]{11})", url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def format_timestamp(seconds: float) -> str:
    """초 단위 시간을 'MM:SS' 또는 'HH:MM:SS' 형식으로 변환합니다."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def get_transcript(video_url_or_id: str, languages=("ko", "en")):
    """
    youtube-transcript-api를 사용하여 자막 목록을 가져옵니다.
    라이브러리 버전(1.x 인스턴스 방식 및 구버전 클래스메서드 방식) 모두 호환됩니다.
    """
    video_id = extract_video_id(video_url_or_id)
    print(f"🎬 대상 비디오 ID: {video_id}")

    try:
        # youtube-transcript-api >= 1.0.0 (인스턴스 방식)
        if hasattr(YouTubeTranscriptApi, "fetch"):
            api = YouTubeTranscriptApi()
            transcript_data = api.fetch(video_id, languages=languages)
            items = transcript_data.to_raw_data()
        else:
            # youtube-transcript-api < 1.0.0 (클래스 메서드 방식)
            items = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)

        return items

    except IpBlocked:
        print("\n[!] YouTube에서 일시적으로 현재 IP의 자막 요청을 차단(429 Too Many Requests)했습니다.")
        print("    -> 잠시 후 다시 시도하거나, VPN/모바일 핫스팟/프록시를 사용해보세요.")
        return None
    except TranscriptsDisabled:
        print("\n[!] 해당 영상은 자막이 비활성화되어 있습니다.")
        return None
    except NoTranscriptFound:
        print(f"\n[!] 요청한 언어({languages})의 자막을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"\n[!] 자막을 가져오는 중 오류가 발생했습니다: {e}")
        return None


def main():
    target_url = "https://www.youtube.com/watch?v=E-sZv8oYGMQ&list=WL&index=6"
    video_id = extract_video_id(target_url)

    print("=" * 60)
    print("유튜브 영상 자막 추출기")
    print(f"URL: {target_url}")
    print("=" * 60)

    # 1. 한국어('ko') 우선, 없을 경우 영어('en') 자막 요청
    transcript = get_transcript(target_url, languages=("ko", "en"))

    if not transcript:
        return

    # 2. 콘솔 출력 (상위 10개 미리보기)
    print(f"\n 총 {len(transcript)}개의 자막 문장을 가져왔습니다.\n")
    print("--- [미리보기 (처음 10문장)] ---")
    for item in transcript[:10]:
        time_str = format_timestamp(item["start"])
        print(f"[{time_str}] {item['text']}")

    # 3. 텍스트 파일로 저장
    output_filename = f"transcript_{video_id}.txt"
    with open(output_filename, "w", encoding="utf-8") as f:
        # 타임스탬프 포함 버전
        f.write("=== 타임스탬프 포함 자막 ===\n\n")
        for item in transcript:
            time_str = format_timestamp(item["start"])
            f.write(f"[{time_str}] {item['text']}\n")

        f.write("\n\n=== 전체 대본 (텍스트만) ===\n\n")
        full_text = " ".join(item["text"] for item in transcript)
        f.write(full_text)

    print(f"\n 파일이 성공적으로 저장되었습니다: {output_filename}")


if __name__ == "__main__":
    main()
