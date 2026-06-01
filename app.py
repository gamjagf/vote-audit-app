
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
.main-title {font-size:2.05rem; font-weight:900; line-height:1.25; color:#252936;}
.sub-text {font-size:1.05rem; color:#666; line-height:1.7;}
.notice {background:#eaf4ff; color:#075985; padding:1rem; border-radius:1rem; font-size:1.02rem; line-height:1.7; margin-top:1rem;}
.warn {background:#fff7ed; color:#9a3412; padding:1rem; border-radius:1rem; font-size:1.02rem; line-height:1.7; margin-top:1rem;}
.step-title {font-size:1.35rem; font-weight:850; margin-top:1.8rem; margin-bottom:.6rem;}
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
        "O": "0", "o": "0", "D": "0",
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
    out = []
    for n in nums:
        try:
            value = int(n)
            if 0 <= value <= 999999:
                out.append(value)
        except:
            pass
    return out

def preprocess_images_for_ocr(image):
    """
    OCR 실패를 줄이기 위해 원본, 확대본, 흑백 대비본, 이진화본을 모두 만든다.
    """
    import cv2

    rgb = np.array(image.convert("RGB"))
    variants = []

    # 1. 원본
    variants.append(("원본", rgb))

    # 2. 2배 확대
    enlarged = cv2.resize(rgb, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    variants.append(("2배 확대", enlarged))

    # 3. 흑백 + 대비 향상
    gray = cv2.cvtColor(enlarged, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    variants.append(("흑백 대비 보정", contrast))

    # 4. adaptive threshold
    th = cv2.adaptiveThreshold(
        contrast,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )
    variants.append(("이진화 보정", th))

    # 5. 약한 샤프닝
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharp = cv2.filter2D(contrast, -1, kernel)
    variants.append(("선명도 보정", sharp))

    return variants

@st.cache_resource
def load_easyocr_reader():
    import easyocr
    # 숫자 위주라 en을 먼저 사용하고, 한글이 섞인 문서라 ko도 함께 사용
    return easyocr.Reader(['en', 'ko'], gpu=False)

def run_ocr(image):
    reader = load_easyocr_reader()
    variants = preprocess_images_for_ocr(image)

    all_text_parts = []
    all_numbers = []

    for name, img in variants:
        try:
            results = reader.readtext(img, detail=0, paragraph=False, contrast_ths=0.05, adjust_contrast=0.7)
            text = "\n".join(results)
            nums = extract_numbers_from_text(text)

            all_text_parts.append(f"[{name}]\n{text}")
            all_numbers.extend(nums)
        except Exception as e:
            all_text_parts.append(f"[{name}] OCR 실패: {e}")

    # 중복은 유지하되 너무 짧은 잡음 제거: 0,1도 필요할 수 있어 유지
    return "\n\n".join(all_text_parts), all_numbers

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
    df = make_default_table()

    # 1~6자리 숫자만 사용
    candidates = [n for n in numbers if 0 <= n <= 999999]

    # 수령매수 후보: 500~20000 사이의 값 중 가장 자주 나오는 값 우선
    received_pool = [n for n in candidates if 500 <= n <= 20000]
    default_received = 0
    if received_pool:
        s = pd.Series(received_pool)
        default_received = int(s.value_counts().index[0])

    for i in range(len(df)):
        df.loc[i, "수령매수"] = default_received

    # 후보 숫자를 표에 초안 입력
    # 실제 정확 자동 입력은 다음 단계의 고정좌표 OCR에서 완성
    fill_cols = [
        "잔여 시작번호",
        "잔여 끝번호",
        "잔여매수 기재값",
        "교부매수 기재값",
        "투표자수계 기재값",
        "선거인명부등재자 기재값",
    ]

    # 0과 1 같은 잡음은 특수유형 칸에 따로 들어갈 수 있어 일단 뒤로 보냄
    main_candidates = [n for n in candidates if n >= 10]
    small_candidates = [n for n in candidates if n < 10]
    ordered = main_candidates + small_candidates

    idx = 0
    for r in range(len(df)):
        for c in fill_cols:
            if idx < len(ordered):
                df.loc[r, c] = int(ordered[idx])
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

        problems = []
        if calc_left != written_left:
            problems.append(f"잔여매수 불일치: 계산 {calc_left:,} / 기재 {written_left:,}")
        if calc_issued != written_issued:
            problems.append(f"교부매수 불일치: 계산 {calc_issued:,} / 기재 {written_issued:,}")
        if written_voters != written_issued:
            problems.append(f"투표자수계 불일치: 투표자수계 {written_voters:,} / 교부매수 {written_issued:,}")
        if calc_registry != written_registry:
            problems.append(f"선거인명부등재자 불일치: 계산 {calc_registry:,} / 기재 {written_registry:,}")

        result_rows.append({
            "선거명": election,
            "잔여매수 계산값": calc_left,
            "교부매수 계산값": calc_issued,
            "특수유형 합계": special_total,
            "선거인명부등재자 계산값": calc_registry,
            "잔여검산": "OK" if calc_left == written_left else "오류",
            "교부검산": "OK" if calc_issued == written_issued else "오류",
            "투표자수검산": "OK" if written_voters == written_issued else "오류",
            "명부등재자검산": "OK" if calc_registry == written_registry else "오류",
            "최종판정": "정상" if not problems else "재확인",
            "비고": "이상 없음" if not problems else " / ".join(problems),
        })
    return pd.DataFrame(result_rows)

st.markdown('<div class="main-title">🗳️ 투표록 7개 선거<br>OCR 자동심사 앱</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">사진을 올리면 여러 이미지 보정 방식으로 OCR 숫자를 자동 인식합니다.</div>', unsafe_allow_html=True)

st.markdown("""
<div class="notice">
<b>OCR 보정 강화 버전</b><br>
① 원본, 확대본, 흑백 대비본, 이진화본, 선명도 보정본을 모두 OCR합니다.<br>
② 인식된 숫자 목록을 보여줍니다.<br>
③ 숫자 자동 입력 초안을 만든 뒤 사용자가 확인·수정합니다.<br>
④ 사진이 흐리거나 숫자가 작으면 OCR 결과가 비어 있을 수 있습니다.
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

    width, height = image.size
    st.caption(f"이미지 크기: {width} × {height}")
    if width < 1200 or height < 1200:
        st.markdown('<div class="warn">사진 해상도가 낮습니다. 숫자가 작거나 흐리면 OCR이 실패할 수 있습니다. 문서 표 부분을 더 크게 촬영해 주세요.</div>', unsafe_allow_html=True)

    st.markdown('<div class="step-title">🤖 2. OCR 숫자 자동 인식</div>', unsafe_allow_html=True)

    if st.button("🔍 OCR로 숫자 자동 인식하기", use_container_width=True):
        with st.spinner("OCR 숫자 인식 중입니다. 첫 실행은 EasyOCR 모델 로딩으로 시간이 걸릴 수 있습니다."):
            try:
                full_text, numbers = run_ocr(image)
                st.session_state.ocr_text = full_text
                st.session_state.ocr_numbers = numbers
                st.session_state.input_df = auto_fill_from_numbers(numbers)

                if len(numbers) == 0:
                    st.warning("OCR이 숫자를 찾지 못했습니다. 표와 숫자가 더 크게 보이도록 다시 촬영해 주세요.")
                else:
                    st.success(f"OCR 숫자 인식 완료: {len(numbers)}개 숫자를 찾았습니다. 아래 표를 확인·수정해 주세요.")
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
st.download_button("📄 심사결과 CSV 다운로드", data=csv, file_name="투표록_심사결과.csv", mime="text/csv", use_container_width=True)

st.markdown('<div class="step-title">📌 촬영 안내</div>', unsafe_allow_html=True)
st.markdown("""
<div class="guide">
1. 숫자가 있는 표 부분을 화면에 크게 채워 촬영해 주세요.<br>
2. 그림자 없이 밝은 곳에서 촬영해 주세요.<br>
3. 초점이 맞지 않으면 OCR 결과가 빈 목록 []으로 나옵니다.<br>
4. 다음 단계의 고정좌표 OCR에서는 양식의 칸 위치를 지정하여 정확도를 더 높일 수 있습니다.<br>
5. 최종 판단 전에는 반드시 원본 투표록과 대조해 주세요.
</div>
""", unsafe_allow_html=True)

st.caption("※ 본 앱은 투표록 심사 보조용입니다. 최종 판단은 공식 선거관리 절차와 원본 서류 확인에 따릅니다.")
