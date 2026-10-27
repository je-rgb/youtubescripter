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
from analyzer import extract_hashtags, summarize_text

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="유튜브 자막 추출 및 핵심 요약기",
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
    if hasattr(YouTubeTranscriptApi, "fetch"):
        api = YouTubeTranscriptApi()
        transcript_data = api.fetch(video_id, languages=languages)
        return transcript_data.to_raw_data()
    else:
        return YouTubeTranscriptApi.get_transcript(video_id, languages=languages)


# -----------------------------------------------------------------------------
# UI 화면 구성
# -----------------------------------------------------------------------------
st.title("🎬 유튜브 자막 추출 & 핵심 요약기")
st.caption("유튜브 영상의 대본을 추출하고, 주요 키워드 해시태그 및 1~5줄 핵심 요약을 생성합니다.")

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

# 세션 상태 초기화
if "raw_transcript" not in st.session_state:
    st.session_state.raw_transcript = None
if "current_video_id" not in st.session_state:
    st.session_state.current_video_id = ""

# 2. 자막 추출 실행 버튼
if st.button("🚀 자막 추출 및 분석하기", type="primary", use_container_width=True):
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

# 3. 분석 및 출력 영역
if st.session_state.raw_transcript:
    items = st.session_state.raw_transcript

    # 전체 평문(plain) 텍스트 및 포맷 텍스트 생성
    full_plain_text = " ".join(item["text"] for item in items)
    if include_timestamp:
        formatted_script = "\n".join(f"[{format_timestamp(item['start'])}] {item['text']}" for item in items)
    else:
        formatted_script = full_plain_text

    tab1, tab2 = st.tabs(["✨ 핵심 요약 & 해시태그", "📋 전체 스크립트"])

    # -------------------------------------------------------------------------
    # TAB 1: 핵심 요약 & 해시태그
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("💡 스크립트 분석 결과")

        # 컨트롤 옵션 (1~5줄 요약, 해시태그 개수 조절)
        cfg_col1, cfg_col2 = st.columns(2)
        with cfg_col1:
            summary_lines = st.slider("요약 문장 수 (1~5줄)", min_value=1, max_value=5, value=3)
        with cfg_col2:
            tag_count = st.slider("추출할 해시태그 개수", min_value=3, max_value=10, value=5)

        # 분석 실행
        hashtags = extract_hashtags(full_plain_text, top_n=tag_count)
        summary_sentences = summarize_text(full_plain_text, num_lines=summary_lines)

        # 1) 해시태그 표시
        st.markdown("##### 🏷️ 주요 키워드 해시태그")
        if hashtags:
            st.info(" ".join(hashtags))
        else:
            st.write("추출된 키워드가 없습니다.")

        # 2) 1~5줄 요약 표시
        st.markdown(f"##### 📝 핵심 내용 요약 ({len(summary_sentences)}줄)")
        summary_display = ""
        for i, sentence in enumerate(summary_sentences, start=1):
            summary_display += f"**{i}.** {sentence}\n\n"
        st.markdown(summary_display)

        # 3) 요약본 및 해시태그 저장 파일 제공
        summary_export_text = (
            f"=== [유튜브 영상 ID: {st.session_state.current_video_id}] 핵심 분석 ===\n\n"
            f"[주요 해시태그]\n"
            f"{' '.join(hashtags)}\n\n"
            f"[{len(summary_sentences)}줄 핵심 요약]\n"
            + "\n".join(f"{i}. {s}" for i, s in enumerate(summary_sentences, 1))
        )

        st.download_button(
            label="💾 해시태그 & 핵심 요약 다운로드 (.txt)",
            data=summary_export_text.encode("utf-8"),
            file_name=f"summary_{st.session_state.current_video_id}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    # -------------------------------------------------------------------------
    # TAB 2: 전체 스크립트
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("📋 추출된 전체 스크립트")
        st.text_area(
            label="스크립트 내용",
            value=formatted_script,
            height=350,
            help="텍스트를 복사하거나 아래 저장 버튼으로 다운로드할 수 있습니다.",
        )

        download_filename = f"transcript_{st.session_state.current_video_id}.txt"
        st.download_button(
            label="💾 전체 스크립트 파일(.txt)로 저장하기",
            data=formatted_script.encode("utf-8"),
            file_name=download_filename,
            mime="text/plain",
            use_container_width=True,
        )
