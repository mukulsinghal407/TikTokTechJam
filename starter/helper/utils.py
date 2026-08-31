import re

from starter.helper.config import TOKEN_RE, STOPWORDS

# 시뮬레이터 신호 감지 (v2_1 override / v2_4 H5 소진).
# Simulator-signal detection (v2_1 override / v2_4 H5 exhaustion).
# v2_8_4_1: override 단어 확장 — start over / scratch that / changed my mind 추가.
#   현재 evaluator 고정 템플릿엔 없는 표현 → public 200 회귀 0 실측 (TS 0.865801 동일).
#   패러프레이즈된 override 를 놓칠 경우 대비한 리콜 확장. agent_v2_8 도 이 심볼을 import 함.
# v2_8_4_1: widens override detection with three reset phrases. Absent from the fixed
#   evaluator templates → zero measured change on public 200; hedges recall against
#   paraphrased override messages. agent_v2_8 imports this symbol too.
_OVERRIDE_RE = re.compile(
    r"ignore my earlier|actually,?\s*(?:ignore|instead)"
    r"|start over|scratch that|changed my mind",
    re.I,
)
_EXHAUST_RE = re.compile(r"preference for\s+([a-z_]+)", re.I)
_JUDGMENT_RE = re.compile(r"use your judgment|use your judgement", re.I)
# H5 소진 감지 + sticky mining 대상. brand/budget 은 수율 0 이라 sticky 는 안 걸리지만,
# "no additional preference for brand" 같은 소진 신호는 잡아야 재질문을 막는다 (v2_4).
# Targets for H5 exhaustion + sticky mining. brand/budget never yield so sticky never fires on them,
# but we must still catch their exhaustion signal ("no additional preference for brand") to stop
# re-asking (v2_4).
_REAL_ATTRS = ("feature", "material", "color", "style", "size", "use_case", "brand", "budget")

def _text(value: object) -> str:
    """카탈로그 필드(문자열/리스트/딕트)를 검색용 평문으로. / Flatten a catalog field to plain text."""
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{k} {v}" for k, v in value.items())
    if isinstance(value, list):
        return " ".join(str(x) for x in value)
    return str(value)


def _terms(text: str) -> list[str]:
    """토큰화 + stopword 제거. / Tokenize and drop stopwords."""
    return [t.lower() for t in TOKEN_RE.findall(text)
            if len(t) > 1 and t.lower() not in STOPWORDS]


def _dedupe(items: list[str]) -> list[str]:
    """순서 보존 중복 제거. / Order-preserving de-duplication."""
    return list(dict.fromkeys(x for x in items if x))


def _fts_expression(terms: list[str]) -> str:
    """토큰 목록을 FTS5 OR 표현식으로. 방어적으로 인용. / Build an FTS5 OR expression; quote defensively."""
    safe = []
    for term in _dedupe(terms)[:48]:
        term = term.replace('"', '""')
        if term:
            safe.append(f'"{term}"')
    return " OR ".join(safe)

export ={
    "_OVERRIDE_RE": _OVERRIDE_RE,
    "_EXHAUST_RE": _EXHAUST_RE,
    "_JUDGMENT_RE": _JUDGMENT_RE,
    "_REAL_ATTRS": _REAL_ATTRS,
    "_text": _text,
    "_terms": _terms,
    "_dedupe": _dedupe,
    "_fts_expression": _fts_expression,
}