import io
import re
import urllib.parse
import streamlit as st
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    IpBlocked,
)

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="유튜브 자막 추출기",
    page_icon="🎬",
    layout="centered",
)


# -----------------------------------------------------------------------------
# 유틸리티 함수
# -----------------------------------------------------------------------------
def extract_video_id(url_or_id: str) -> str:
    """유튜브 URL 또는 영상 ID에서 11자리 비디오 ID를 추출합니다."""
    url_or_id = url_or_id.strip()
    if "youtube.com" in url_or_id or "youtu.be" in url_or_id:
        parsed = urllib.parse.urlparse(url_or_id)
        if "youtu.be" in parsed.netloc:
            return parsed.path.lstrip("/")
        query = urllib.parse.parse_qs(parsed.query)
        if "v" in query:
            return query["v"][0]

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


def fetch_transcript(video_id: str, languages=("ko", "en")):
    """youtube-transcript-api를 통해 자막 데이터를 가져옵니다."""
    # youtube-transcript-api >= 1.0.0 (인스턴스 방식)
    if hasattr(YouTubeTranscriptApi, "fetch"):
        api = YouTubeTranscriptApi()
        transcript_data = api.fetch(video_id, languages=languages)
        return transcript_data.to_raw_data()
    else:
        # youtube-transcript-api < 1.0.0 (클래스 메서드 방식)
        return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)


# -----------------------------------------------------------------------------
# UI 화면 구성
# -----------------------------------------------------------------------------
st.title("🎬 유튜브 자막/대본 추출기")
st.caption("유튜브 영상의 링크를 입력하면 자동으로 자막을 추출하고 파일로 저장할 수 있습니다.")

# 1. 입력 영역 (Input)
youtube_url = st.text_input(
    label="유튜브 영상 주소 (URL) 또는 영상 ID",
    value="https://www.youtube.com/watch?v=eThHVECmKVc&list=WL&index=4",
    placeholder="예: https://www.youtube.com/watch?v=...",
)

col1, col2 = st.columns(2)
with col1:
    primary_lang = st.selectbox("우선 언어", options=["ko (한국어)", "en (영어)", "ja (일본어)"], index=0)
with col2:
    include_timestamp = st.checkbox("타임스탬프 포함하여 보기", value=True)

lang_code = primary_lang.split()[0]
languages = (lang_code, "ko", "en") if lang_code not in ("ko", "en") else (lang_code, "en" if lang_code == "ko" else "ko")

# 상태 세션 초기화
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = ""
if "raw_transcript" not in st.session_state:
    st.session_state.raw_transcript = None
if "current_video_id" not in st.session_state:
    st.session_state.current_video_id = ""

# 2. 자막 추출 실행 버튼
if st.button("🚀 자막 추출하기", type="primary", use_container_width=True):
    if not youtube_url.strip():
        st.warning("⚠️ 유튜브 영상 주소를 입력해 주세요.")
    else:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            st.error("유효하지 않은 유튜브 URL 형식입니다.")
        else:
            with st.spinner(f"비디오({video_id})의 자막을 불러오는 중입니다..."):
                try:
                    transcript_items = fetch_transcript(video_id, languages=languages)
                    st.session_state.raw_transcript = transcript_items
                    st.session_state.current_video_id = video_id
                    st.success("자막을 성공적으로 가져왔습니다!")
                except IpBlocked:
                    st.error("🚨 YouTube에서 현재 IP의 자막 요청을 일시 차단(429)했습니다. 잠시 후 시도하거나 테더링/VPN을 이용해보세요.")
                    st.session_state.raw_transcript = None
                except TranscriptsDisabled:
                    st.error("⚠️ 해당 영상은 자막이 비활성화되어 있습니다.")
                    st.session_state.raw_transcript = None
                except NoTranscriptFound:
                    st.error(f"⚠️ 요청한 언어({languages})에 해당하는 자막이 없습니다.")
                    st.session_state.raw_transcript = None
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
                    st.session_state.raw_transcript = None

# 3. 출력 영역 (Output) 및 저장 버튼
if st.session_state.raw_transcript:
    items = st.session_state.raw_transcript

    # 타임스탬프 포함/미포함 텍스트 생성
    if include_timestamp:
        formatted_text = "\n".join(f"[{format_timestamp(item['start'])}] {item['text']}" for item in items)
    else:
        formatted_text = " ".join(item["text"] for item in items)

    st.subheader("📋 추출된 스크립트")
    st.text_area(
        label="스크립트 내용",
        value=formatted_text,
        height=320,
        help="텍스트를 복사하거나 아래 저장 버튼으로 다운로드할 수 있습니다.",
    )

    # 4. 저장 (다운로드) 버튼
    download_filename = f"transcript_{st.session_state.current_video_id}.txt"
    st.download_button(
        label="💾 텍스트 파일(.txt)로 저장하기",
        data=formatted_text.encode("utf-8"),
        file_name=download_filename,
        mime="text/plain",
        use_container_width=True,
    )
