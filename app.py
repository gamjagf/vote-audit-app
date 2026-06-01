
import streamlit as st
import pandas as pd
from PIL import Image
import re
import numpy as np

st.set_page_config(
    page_title="투표록 7개 선거 OCR 자동심사 앱",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.block-container {padding-top:1rem; padding-bottom:2rem;}
.main-title {font-size:2.1rem; font-weight:900; line-height:1.25; color:#252936;}
.sub-text {font-size:1.05rem; color:#666; line-height:1.7;}
.notice {background:#eaf4ff; color:#075985; padding:1rem; border-radius:1rem; font-size:1.02rem; line-height:1.7; margin-top:1rem;}
.step-title {font-size:1.4rem; font-weight:850; margin-top:1.8rem; margin-bottom:.6rem;}
.ok-box {background:#eaf8ef; border-left:7px solid #22a35a; padding:1rem; border-radius:1rem; font-size:1.05rem;}
.bad-box {background:#fff0f0; border-left:7px solid #e5484d; padding:1rem; border-radius:1rem; font-size:1.05rem;}
.guide {background:#f7f7f8; padding:1rem; border-radius:1rem; line-height:1.8;}
</style>
""", unsafe_allow_html=True)

def to_int(value):
    try:
        if pd.isna(value):
            return 0
        return int(str(value).replace(",", "").strip())
    except Exception:
        return 0

def clean_number_text(text):
    text = str(text)
    replace_map = {
        "O": "0", "o": "0",
        "I": "1", "l": "1", "|": "1",
        "S": "5", "s": "5",
        "B": "8",
        ",": "",
        " ": ""
    }
    for k, v in replace_map.items():
        text = text.replace(k, v)
    return text

def extract_numbers_from_text(text):
    text = clean_number_text(text)
    nums = re.findall(r"\d+", text)
    result = []
    for n in nums:
        try:
            value = int(n)
            if value >= 0:
                result.append(value)
        except:
            pass
    return result

@st.cache_resource
def load_easyocr_reader():
    import easyocr
    return easyocr.Reader(['ko', 'en'], gpu=False)

def run_ocr(image):
    reader = load_easyocr_reader()
    img_np = np.array(image)
    results = reader.readtext(img_np, detail=0, paragraph=False)
    full_text = "\n".join(results)
    numbers = extract_numbers_from_text(full_text)
    return full_text, numbers

def make_default_table():
    elections = [
        "교육감 선거",
        "도지사 선거",
        "시장·군수·구청장 선거",
        "지역구 도의원 선거",
        "비례대표 도의원 선거",
        "지역구 시·군의원 선거",
        "비례대표 시·군의원 선거",
    ]
    rows = []
    for name in elections:
        rows.append({
            "선거명": name,
            "수령매수": 0,
            "잔여 시작번호": 0,
            "잔여 끝번호": 0,
            "오·훼손 미교부": 0,
            "잔여매수 기재값": 0,
            "교부매수 기재값": 0,
            "투표자수계 기재값": 0,
            "거소 미발송·반송": 0,
            "결정서 지참": 0,
            "거소투표용지·회송봉투 반납": 0,
            "귀국투표자": 0,
            "선거인명부등재자 기재값": 0,
        })
    return pd.DataFrame(rows)

def auto_fill_from_numbers(numbers):
    """
    OCR 숫자 목록을 기반으로 자동 입력 후보를 만든다.
    고정 좌표 OCR 전 단계의 임시 자동 입력 방식이다.
    실제 양식 보정 후에는 이 부분을 좌표 기반으로 교체한다.
    """
    df = make_default_table()

    # 자주 나오는 구조 예시:
    # 수령매수 3500, 교부매수 2903, 잔여매수 597 등이 반복될 가능성을 고려
    useful = [n for n in numbers if n >= 0]

    # 3자리~5자리 숫자를 우선 후보로 사용
    candidates = [n for n in useful if 1 <= n <= 99999]

    # 수령매수 후보: 500 이상 숫자 중 반복값 또는 큰 값
    received_candidates = [n for n in candidates if n >= 500]
    default_received = received_candidates[0] if received_candidates else 0

    for i in range(len(df)):
        df.loc[i, "수령매수"] = default_received

    # 숫자를 7개 선거에 순서대로 배분할 수 있도록 후보값을 일부 채움
    # 정확 자동화가 아니라 "자동 입력 초안" 기능
    idx = 0
    cols = [
        "잔여 시작번호",
        "잔여 끝번호",
        "잔여매수 기재값",
        "교부매수 기재값",
        "투표자수계 기재값",
        "선거인명부등재자 기재값",
    ]

    for row in range(len(df)):
        for col in cols:
            if idx < len(candidates):
                df.loc[row, col] = candidates[idx]
                idx += 1

    return df

def audit_table(df):
    result_rows = []
    for _, row in df.iterrows():
        election = row["선거명"]
        received = to_int(row["수령매수"])
        start_no = to_int(row["잔여 시작번호"])
        end_no = to_int(row["잔여 끝번호"])
        damaged = to_int(row["오·훼손 미교부"])
        written_left = to_int(row["잔여매수 기재값"])
        written_issued = to_int(row["교부매수 기재값"])
        written_voters = to_int(row["투표자수계 기재값"])
        home_return = to_int(row["거소 미발송·반송"])
        decision_doc = to_int(row["결정서 지참"])
        envelope_return = to_int(row["거소투표용지·회송봉투 반납"])
        overseas = to_int(row["귀국투표자"])
        written_registry = to_int(row["선거인명부등재자 기재값"])

        calc_left = end_no - start_no + 1 + damaged if start_no > 0 and end_no >= start_no else 0
        calc_issued = received - calc_left if received >= calc_left else -1
        special_total = home_return + decision_doc + envelope_return + overseas
        calc_registry = written_voters - special_total

        check_left = calc_left == written_left
        check_issued = calc_issued == written_issued
        check_voters = written_voters == written_issued
        check_registry = calc_registry == written_registry

        problems = []
        if not check_left:
            problems.append(f"잔여매수 불일치: 계산 {calc_left:,} / 기재 {written_left:,}")
        if not check_issued:
            problems.append(f"교부매수 불일치: 계산 {calc_issued:,} / 기재 {written_issued:,}")
        if not check_voters:
            problems.append(f"투표자수계 불일치: 투표자수계 {written_voters:,} / 교부매수 {written_issued:,}")
        if not check_registry:
            problems.append(f"선거인명부등재자 불일치: 계산 {calc_registry:,} / 기재 {written_registry:,}")

        result_rows.append({
            "선거명": election,
            "잔여매수 계산값": calc_left,
            "교부매수 계산값": calc_issued,
            "특수유형 합계": special_total,
            "선거인명부등재자 계산값": calc_registry,
            "잔여검산": "OK" if check_left else "오류",
            "교부검산": "OK" if check_issued else "오류",
            "투표자수검산": "OK" if check_voters else "오류",
            "명부등재자검산": "OK" if check_registry else "오류",
            "최종판정": "정상" if not problems else "재확인",
            "비고": "이상 없음" if not problems else " / ".join(problems),
        })
    return pd.DataFrame(result_rows)

st.markdown('<div class="main-title">🗳️ 투표록 7개 선거<br>OCR 자동심사 앱</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">사진을 올리면 OCR로 숫자를 자동 인식하고, 인식된 숫자를 바탕으로 7개 선거를 검산합니다.</div>', unsafe_allow_html=True)

st.markdown("""
<div class="notice">
<b>OCR 자동 인식 버전</b><br>
① 사진에서 숫자를 자동으로 읽습니다.<br>
② OCR 결과 숫자 목록을 보여줍니다.<br>
③ 자동 입력 초안을 만들고, 사용자가 확인·수정할 수 있습니다.<br>
④ 최종 검산은 수정된 표 기준으로 자동 수행됩니다.
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="step-title">📷 1. 투표록 사진 올리기</div>', unsafe_allow_html=True)

tab_file, tab_camera = st.tabs(["📁 사진 선택", "📷 카메라 촬영"])
uploaded_image = None

with tab_file:
    uploaded_image = st.file_uploader("갤러리에서 투표록 사진을 선택하세요.", type=["jpg", "jpeg", "png"])

with tab_camera:
    camera_image = st.camera_input("카메라로 투표록을 촬영하세요.")
    if camera_image is not None:
        uploaded_image = camera_image

if "input_df" not in st.session_state:
    st.session_state.input_df = make_default_table()

if uploaded_image is not None:
    image = Image.open(uploaded_image).convert("RGB")
    st.image(image, caption="업로드된 투표록 이미지", use_container_width=True)

    st.markdown('<div class="step-title">🤖 2. OCR 숫자 자동 인식</div>', unsafe_allow_html=True)

    if st.button("🔍 OCR로 숫자 자동 인식하기", use_container_width=True):
        with st.spinner("OCR 숫자 인식 중입니다. 첫 실행은 시간이 다소 걸릴 수 있습니다."):
            try:
                full_text, numbers = run_ocr(image)
                st.session_state.ocr_text = full_text
                st.session_state.ocr_numbers = numbers
                st.session_state.input_df = auto_fill_from_numbers(numbers)
                st.success("OCR 숫자 인식이 완료되었습니다. 아래 표의 자동 입력값을 확인·수정해 주세요.")
            except Exception as e:
                st.error("OCR 실행 중 오류가 발생했습니다.")
                st.write(e)

if "ocr_numbers" in st.session_state:
    st.markdown('<div class="step-title">🔢 OCR 인식 숫자 목록</div>', unsafe_allow_html=True)
    st.write(st.session_state.ocr_numbers)

    with st.expander("OCR 원문 보기"):
        st.text(st.session_state.get("ocr_text", ""))

st.markdown('<div class="step-title">🧾 3. 선거별 숫자 확인·수정</div>', unsafe_allow_html=True)
st.markdown("""
<div class="guide">
OCR 자동 입력값은 사진 상태에 따라 틀릴 수 있습니다.<br>
반드시 원본 투표록과 비교하여 숫자를 확인·수정한 뒤 심사 결과를 보세요.
</div>
""", unsafe_allow_html=True)

edited_df = st.data_editor(
    st.session_state.input_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
    key="audit_editor"
)

st.session_state.input_df = edited_df

st.markdown('<div class="step-title">✅ 4. 자동 심사 결과</div>', unsafe_allow_html=True)

result_df = audit_table(edited_df)

ok_count = int((result_df["최종판정"] == "정상").sum())
bad_count = int((result_df["최종판정"] == "재확인").sum())

c1, c2, c3 = st.columns(3)
c1.metric("전체 선거", len(result_df))
c2.metric("정상", ok_count)
c3.metric("재확인", bad_count)

st.dataframe(result_df, use_container_width=True, hide_index=True)

if bad_count == 0:
    st.markdown('<div class="ok-box"><b>7개 선거 모두 검산 결과 정상입니다.</b></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="bad-box"><b>재확인 필요한 선거가 있습니다.</b><br>비고란의 불일치 항목을 원본 투표록과 대조해 주세요.</div>', unsafe_allow_html=True)

csv = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "📄 심사결과 CSV 다운로드",
    data=csv,
    file_name="투표록_심사결과.csv",
    mime="text/csv",
    use_container_width=True
)

st.markdown('<div class="step-title">📌 촬영 안내</div>', unsafe_allow_html=True)
st.markdown("""
<div class="guide">
1. 문서를 책상 위에 평평하게 놓아 주세요.<br>
2. 그림자가 생기지 않도록 밝은 곳에서 촬영해 주세요.<br>
3. 표 전체가 화면 안에 들어오도록 촬영해 주세요.<br>
4. 숫자가 흐리게 보이면 OCR 인식률이 낮아집니다.<br>
5. 최종 판단 전에는 반드시 원본 투표록과 대조해 주세요.
</div>
""", unsafe_allow_html=True)

st.caption("※ 본 앱은 투표록 심사 보조용입니다. 최종 판단은 공식 선거관리 절차와 원본 서류 확인에 따릅니다.")
