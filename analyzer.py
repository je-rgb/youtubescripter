import os
import re
from collections import Counter
from typing import List, Tuple, Optional

# ---------------------------------------------------------------------------
# 한국어/영어 불용어 (Stopwords) 목록
# ---------------------------------------------------------------------------
KOREAN_STOPWORDS = {
    # 대명사 / 지시어
    "그것", "이것", "저것", "여기", "거기", "저기", "우리", "너희", "그들", "저희", "당신",
    "여러분", "자신", "누구", "무엇", "어디", "언제", "어떻게", "어떤", "이런", "그런", "저런",
    "저는", "제가", "내가", "나를", "나의", "내게", "제게",
    # 용언 활용형 (동사/형용사/보조용언)
    "하는", "하고", "해서", "하면", "하며", "하세요", "하지", "해야", "하려고", "합니다",
    "되는", "되고", "돼서", "되면", "되세요", "되지", "된다", "됩니다", "되었", "됐다",
    "있는", "있고", "있어", "있으면", "있으며", "있지", "있다", "있던", "있습니다",
    "없는", "없고", "없어", "없으면", "없으며", "없지", "없다", "없던", "없습니다",
    "보는", "보고", "봐서", "보면", "보세요", "보며", "보다",
    "가는", "가고", "가서", "가면", "오고", "오면", "와서",
    "주는", "주고", "줘서", "주면", "받고", "받아", "받은",
    "같은", "같이", "같아", "같아요", "같다",
    "거예요", "거죠", "거야", "건가요", "게요", "텐데", "테니", "때문",
    "입니다", "이에요", "예요", "입니까", "이라", "이다",
    # 빈출 일반 명사 / 의존 명사 / 형식 명사
    "생각", "정도", "사실", "마음", "경우", "부분", "가지", "하나", "사람", "사람들",
    "시간", "시작", "오늘", "내일", "어제", "지금", "하루", "이번", "지난", "다음", "동안",
    "모든", "다른", "여러", "각각", "서로", "이후", "이전", "관련", "이유", "방법", "모습", "가지고",
    # 빈출 부사 / 감탄사 / 연결어
    "진짜", "정말", "너무", "되게", "약간", "그냥", "아주", "매우", "항상", "자주",
    "이제", "다시", "계속", "먼저", "함께", "그리고", "그러나", "하지만", "그런데", "근데",
    "그래서", "그러면", "또한", "혹시", "만약", "바로", "어쨌든", "아무튼", "글쎄",
    "일단", "하여튼", "뭔가", "약간의", "그렇게", "이렇게", "저렇게", "앞으로", "스스로",
    "제대로", "진심으로", "정도로", "마찬가지로", "살짝", "요즘", "앞으", "토버",
}

# 단어 뒤에 붙는 한국어 조사/어미 접미사 패턴 (긴 접미사부터 매칭하여 제거)
JOSA_PATTERNS = [
    r"(에서는|으로는|에게는|한테는|부터는|까지는|에서의|으로서|으로써)$",
    r"(에서|으로|에게|한테|부터|까지|하고|이며|이나|처럼|만큼|보다|마저|조차|밖에|이란|이야)$",
    r"(에는|에도|의도|을도|를도|은도|는도|이가|이다|이며|이면)$",
    r"(은|는|이|가|을|를|의|에|로|와|과|도|만|랑)$",
]

ENGLISH_STOPWORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not",
    "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from",
    "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would",
    "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which",
    "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know",
    "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
    "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
    "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
}


def clean_transcript_text(text: str) -> str:
    """타임스탬프([00:00] 등) 및 특수 헤더를 제거하고 순수 텍스트로 정제합니다."""
    # '[00:00]' 또는 '[01:23:45]' 타임스탬프 제거
    cleaned = re.sub(r"\[\d{1,2}:\d{2}(?::\d{2})?\]", "", text)
    # 구분선이나 제목 라인 제거
    cleaned = re.sub(r"===.*?===", "", cleaned)
    # 연속 공백 정리
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned.strip()


def normalize_korean_word(word: str) -> str:
    """한국어 단어 끝에 붙은 조사를 제거하여 명사 원형을 추정합니다."""
    # 특정 부사는 조사 분리 예외
    if word in {"앞으로", "스스로", "제대로", "진심으로"}:
        return word

    for pattern in JOSA_PATTERNS:
        stem = re.sub(pattern, "", word)
        if len(stem) >= 2 and stem != word:
            return stem
    return word


def extract_keywords(text: str, top_n: int = 5) -> List[Tuple[str, int]]:
    """
    텍스트에서 반복 등장하는 핵심 키워드와 빈도수를 추출합니다.
    불용어, 조사, 구어체 어미를 필터링합니다.
    """
    cleaned = clean_transcript_text(text)
    tokens = re.findall(r"[가-힣a-zA-Z0-9]{2,}", cleaned)

    candidate_words = []
    for token in tokens:
        lower_token = token.lower()

        # 영문 불용어
        if lower_token in ENGLISH_STOPWORDS:
            continue

        # 순수 숫자
        if token.isdigit():
            continue

        # 한글 처리
        if re.search(r"[가-힣]", token):
            stem = normalize_korean_word(token)
            if stem in KOREAN_STOPWORDS or len(stem) < 2:
                continue
            # 서술격 조사나 종결형이 붙은 단어 필터
            if stem.endswith(("하다", "되다", "이다", "있다", "없다", "해요", "돼요", "예요")):
                continue
            candidate_words.append(stem)
        else:
            if lower_token in KOREAN_STOPWORDS:
                continue
            candidate_words.append(token)

    if not candidate_words:
        return []

    counter = Counter(candidate_words)
    return counter.most_common(top_n)


def extract_hashtags(text: str, top_n: int = 5) -> List[str]:
    """
    반복되는 핵심 단어를 '#단어' 형태의 해시태그 리스트로 반환합니다.
    예: ['#목표', '#습관', '#집중', '#실천', '#성공']
    """
    keywords_with_count = extract_keywords(text, top_n=top_n)
    return [f"#{word}" for word, _ in keywords_with_count]


def split_into_sentences(text: str) -> List[str]:
    """자막 텍스트를 온전한 문장 단위로 분할합니다."""
    cleaned = clean_transcript_text(text)

    # 1. 줄바꿈을 공백으로 합침
    flat_text = " ".join(line.strip() for line in cleaned.splitlines() if line.strip())

    # 2. 마침표, 느낌표, 물음표 기준 분할
    raw_sentences = re.split(r"(?<=[.?!])\s+", flat_text)

    sentences = []
    for s in raw_sentences:
        s = s.strip()
        # 문장 길이가 너무 길고 구어체 종결어미(요/다/죠/네/니다)가 있는 경우 분할
        if len(s) > 110:
            sub_parts = re.split(r"(?<=[요다죠네][\s,])\s*", s)
            for part in sub_parts:
                part = part.strip()
                if len(part) >= 15:
                    sentences.append(part)
        else:
            if len(s) >= 12:
                sentences.append(s)

    return sentences if sentences else [cleaned[:100]]


def summarize_text(text: str, num_lines: int = 3) -> List[str]:
    """
    텍스트에서 중요한 핵심 문장을 1~5줄로 추출 요약합니다.
    (핵심 단어 빈도 가중치 + 위치 점수 + 문장 간 다양성 알고리즘)

    :param text: 추출된 자막 스크립트 원문
    :param num_lines: 요약할 줄 수 (1~5줄)
    :return: 1~5개의 핵심 요약 문장 리스트
    """
    num_lines = max(1, min(5, num_lines))  # 1~5줄 범위 보정

    sentences = split_into_sentences(text)
    if not sentences:
        return ["요약할 수 있는 본문 내용이 충분하지 않습니다."]

    if len(sentences) <= num_lines:
        return sentences

    # 1. 상위 핵심 키워드 가중치 수집
    keywords_with_count = extract_keywords(text, top_n=40)
    word_weights = {word: count for word, count in keywords_with_count}

    if not word_weights:
        step = max(1, len(sentences) // num_lines)
        return sentences[::step][:num_lines]

    # 2. 각 문장의 중요도 채점
    sentence_scores = []
    for idx, sentence in enumerate(sentences):
        score = 0.0
        matched_words = 0
        for word, weight in word_weights.items():
            if word in sentence:
                score += weight
                matched_words += 1

        char_len = len(sentence)
        # 30~85자 사이의 핵심 문장에 가산점
        length_factor = 1.0
        if char_len < 25:
            length_factor = 0.6
        elif char_len > 110:
            length_factor = 0.85

        # 위치 가중치 (시작 및 마무리 부분 가산점)
        pos_ratio = idx / len(sentences)
        pos_factor = 1.2 if (pos_ratio < 0.15 or pos_ratio > 0.85) else 1.0

        final_score = (score / (matched_words + 1)) * matched_words * length_factor * pos_factor
        sentence_scores.append((idx, sentence, final_score))

    # 3. 중요도 순으로 정렬 후 상위 문장 선택 (유사 문장 중복 배제)
    sorted_by_score = sorted(sentence_scores, key=lambda x: x[2], reverse=True)

    selected_indices = []
    selected_sentences = []

    for idx, sentence, _ in sorted_by_score:
        if len(selected_indices) >= num_lines:
            break

        sentence_words = set(re.findall(r"[가-힣a-zA-Z0-9]{2,}", sentence))
        is_redundant = False

        for existing in selected_sentences:
            exist_words = set(re.findall(r"[가-힣a-zA-Z0-9]{2,}", existing))
            if sentence_words and exist_words:
                overlap = len(sentence_words & exist_words) / min(len(sentence_words), len(exist_words))
                if overlap > 0.65:
                    is_redundant = True
                    break

        if not is_redundant:
            selected_indices.append(idx)
            selected_sentences.append(sentence)

    # 4. 문맥 순서대로 정렬
    selected_indices.sort()
    ordered_summary = [sentences[i] for i in selected_indices]
    return ordered_summary
