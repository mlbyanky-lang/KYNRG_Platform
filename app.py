import streamlit as st
import pandas as pd

st.set_page_config(page_title="김영편입 AI 통합 관리 시스템", page_icon="🏫", layout="wide")

# ==========================================
# 0. 구글 시트 마스터 DB 연결 설정
# ==========================================
SHEET_ID = "1pp9Sjm-XkX3Xi443eRL7C-9jaEt8nbL9Cg-6fJXauUM"

def get_sheet_url(sheet_name):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name}"

@st.cache_data(ttl=600)
def load_data(sheet_name):
    try:
        df = pd.read_csv(get_sheet_url(sheet_name))
        return df
    except Exception as e:
        st.error(f"'{sheet_name}' 데이터를 불러오는 중 오류가 발생했습니다. 구글 시트 이름을 확인해주세요.")
        return pd.DataFrame()

# ==========================================
# 1. 사이드바 네비게이션
# ==========================================
st.sidebar.title("🏫 김영편입 노량진")

menu = st.sidebar.radio("📌 메뉴 이동", [
    "🏠 메인 홈 (공지사항)", 
    "📖 데일리 암기장", 
    "📝 실전 단어 테스트 (뜻 맞추기)",
    "📝 동의어 문맥 추론 테스트",
    "🔒 관리자 대시보드"
])

st.sidebar.divider()
st.sidebar.caption("© 2026 김영편입 노량진 AI LMS")

# ==========================================
# 2. 메뉴별 화면 라우팅
# ==========================================
if menu == "🏠 메인 홈 (공지사항)":
    st.title("🏠 환영합니다!")
    student_class = st.selectbox("소속 반 선택:", ["CLASS E", "CLASS C", "CLASS BD", "CLASS BJ", "CLASS A"])
    st.info(f"**{student_class}** 학생들, 오늘도 힘내세요! 🔥")

elif menu == "📖 데일리 암기장":
    st.title("📖 데일리 암기장")
    book_choice = st.selectbox("📚 학습할 교재를 선택하세요:", ["MVP1", "MVP2"])
    
    if st.button("데이터 불러오기 테스트"):
        df = load_data(f"{book_choice}_뜻쓰기")
        if not df.empty:
            st.success(f"{book_choice}_뜻쓰기 시트를 성공적으로 불러왔습니다! (총 {len(df)}단어)")
            st.dataframe(df.head())

elif menu == "📝 실전 단어 테스트 (뜻 맞추기)":
    st.title("📝 객관식 단어 테스트 (뜻 맞추기)")
    book_choice = st.selectbox("📚 교재 선택:", ["MVP1", "MVP2"])
    st.write(f"*(향후 '{book_choice}_뜻쓰기' 시트에서 데이터를 가져와 출제합니다)*")

elif menu == "📝 동의어 문맥 추론 테스트":
    st.title("📝 동의어 문맥 추론 테스트")
    book_choice = st.selectbox("📚 교재 선택:", ["MVP1", "MVP2"])
    st.write(f"*(향후 '{book_choice}_동의어' 시트에서 예문과 정답을 가져와 출제합니다)*")

elif menu == "🔒 관리자 대시보드":
    st.title("🔒 원장님 전용 관리자 페이지")
    pwd = st.text_input("관리자 비밀번호를 입력하세요:", type="password")
    
    if pwd == "1234":
        st.success("✅ 관리자 로그인 성공")
        tab1, tab2 = st.tabs(["📝 시험 출제/관리", "📊 성적 및 출결 현황"])
        with tab1:
            st.subheader("데일리 테스트 출제 설정")
        with tab2:
            st.subheader("실시간 성적 및 미응시생 조회")
    elif pwd:
        st.error("비밀번호가 일치하지 않습니다.")