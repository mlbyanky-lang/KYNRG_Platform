import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="김영편입 AI 통합 관리 시스템", page_icon="🏫", layout="wide")

# ==========================================
# 0. 💥 깨진 인코딩 및 특수문자 완벽 방어 엔진 💥
# ==========================================
@st.cache_data
def load_data(file_type, book_choice):
    try:
        if file_type == "뜻쓰기":
            filename = f"{book_choice}.csv"
            # utf-8-sig와 깨진 줄바꿈(\r)을 완벽히 흡수하여 읽어옵니다.
            df = pd.read_csv(filename, encoding='utf-8-sig', on_bad_lines='skip')
            
            # 컬럼명의 공백과 대소문자를 강제로 초기화합니다.
            df.columns = df.columns.str.strip().str.lower()
            
            # 시스템 규격에 맞게 컬럼명 재정의
            if 'word' in df.columns and 'meaning' in df.columns:
                # day 컬럼이 깨졌을 경우를 대비해 보정
                day_col = [c for c in df.columns if 'day' in c]
                if day_col:
                    df.rename(columns={day_col[0]: 'DAY', 'word': 'word', 'meaning': 'meaning'}, inplace=True)
                else:
                    df['DAY'] = 'DAY 01' # 방어 코드
                return df
            else:
                # 컬럼명이 아예 뭉개졌을 경우 강제로 인덱스로 매핑 (0번: DAY, 1번: 단어, 2번: 뜻)
                df = pd.read_csv(filename, encoding='utf-8-sig', header=None, skiprows=1, on_bad_lines='skip')
                df.columns = ['DAY', 'word', 'meaning'] + list(df.columns[3:])
                return df
        else:
            # 동의어 파일 연동 (특수문자 엑셀 규격 방어)
            filename = f"{book_choice}예문(Day1_60)_작업.xlsx - Vol.1 Day 1~30.csv"
            df = pd.read_csv(filename, encoding='utf-8-sig', on_bad_lines='skip')
            df.columns = df.columns.str.strip()
            
            # '데이' 또는 'day'로 시작하는 컬럼 강제 통일
            day_col = [c for c in df.columns if '데이' in c or 'day' in c or 'DAY' in c]
            if day_col: df.rename(columns={day_col[0]: 'DAY'}, inplace=True)
            return df
            
    except Exception as e:
        st.error(f"🚨 {book_choice} 파일 가공 중 오류가 발생했습니다.")
        st.info(f"상세 원인: {e}")
        return pd.DataFrame()

# 관리자 배포용 세션 제어값 초기화
if "test_active" not in st.session_state: st.session_state.test_active = False
if "test_config" not in st.session_state: st.session_state.test_config = {}

# ==========================================
# 1. 사이드바 메뉴 네비게이션
# ==========================================
st.sidebar.title("🏫 김영편입 노량진")
menu = st.sidebar.radio("📌 메뉴 이동", ["📢 반별 공지사항", "📖 데일리 암기장", "📝 실전 단어 테스트", "🔒 관리자 대시보드"])
st.sidebar.divider()
st.sidebar.caption("© 2026 김영편입 노량진 AI LMS")

# ==========================================
# 2. 메인 화면 구현부
# ==========================================

if menu == "📢 반별 공지사항":
    st.title("📢 반별 공지사항 및 안내")
    student_class = st.selectbox("소속 반을 선택하세요:", ["CLASS E", "CLASS C", "CLASS BD", "CLASS BJ", "CLASS A"])
    st.success(f"**{student_class}** 학생들을 위한 실시간 안내 창입니다.")
    st.info("🔥 [공지] 오늘의 데일리 테스트 범위가 업로드되었습니다. 마감 시간 전까지 전원 응시 완료 바랍니다.")

elif menu == "📖 데일리 암기장":
    st.title("📖 데일리 암기 플래시카드")
    col1, col2 = st.columns(2)
    with col1: book_choice = st.selectbox("📚 교재 선택:", ["MVP1", "MVP2"])
    
    df = load_data("뜻쓰기", book_choice)
    if not df.empty:
        # 데이터 정제 (DAY 문자열에서 숫자만 추출)
        df['DAY_NUM'] = df['DAY'].astype(str).str.extract(r'(\d+)').fillna(1).astype(int)
        days = sorted(df['DAY_NUM'].unique())
        with col2: target_day = st.selectbox("📅 학습할 DAY 선택:", [f"DAY {d:02d}" for d in days])
        
        target_num = int(target_day.split()[1])
        day_df = df[df['DAY_NUM'] == target_num]
        st.subheader(f"✨ {book_choice} - {target_day} 핵심 암기 단어")
        st.dataframe(day_df[['word', 'meaning']].reset_index(drop=True), use_container_width=True)

elif menu == "📝 실전 단어 테스트":
    st.title("📝 실전 데일리 테스트")
    
    if not st.session_state.test_active:
        st.warning("🔒 현재 활성화된 시험이 없습니다. 원장님이 관리자 대시보드에서 시험을 출제할 때까지 기다려주세요.")
    else:
        config = st.session_state.test_config
        st.info(f"🎯 오늘의 시험: **{config['book']} ({config['type']})** | 범위: **DAY {config['start']} ~ {config['end']}**")
        
        s_class = st.selectbox("본인의 반을 선택하세요:", ["CLASS E", "CLASS C", "CLASS BD", "CLASS BJ", "CLASS A"])
        s_name = st.text_input("이름을 입력하세요:")
        
        if s_name:
            if "start_exam" not in st.session_state: st.session_state.start_exam = False
            if st.button("🚀 시험지 생성 및 시작") or st.session_state.start_exam:
                st.session_state.start_exam = True
                st.divider()
                raw_df = load_data(config['type'], config['book'])
                
                if not raw_df.empty:
                    if config['type'] == "뜻쓰기":
                        raw_df['DAY_NUM'] = raw_df['DAY'].astype(str).str.extract(r'(\d+)').fillna(1).astype(int)
                        filtered_df = raw_df[(raw_df['DAY_NUM'] >= config['start']) & (raw_df['DAY_NUM'] <= config['end'])]
                        
                        if len(filtered_df) == 0: st.error("범위 내 데이터 부족")
                        else:
                            q_count = min(50, len(filtered_df))
                            q_df = filtered_df.sample(n=q_count, random_state=42).reset_index(drop=True)
                            all_meanings = raw_df['meaning'].dropna().unique().tolist()
                            
                            score = 0
                            for idx, row in q_df.iterrows():
                                st.markdown(f"##### Q{idx+1}. `{row['word']}` 의 뜻은?")
                                correct = row['meaning']
                                distractors = random.sample([m for m in all_meanings if m != correct], min(3, len(all_meanings)-1))
                                options = list(set([correct] + distractors))
                                random.shuffle(options)
                                ans = st.radio(f"선택 (Q{idx+1})", options, key=f"q_{idx}", index=None)
                                if ans == correct: score += 1
                                st.divider()
                            if st.button("🎯 최종 답안 제출"):
                                st.balloons()
                                st.success(f"💯 {s_name} 학생 제출 완료! 점수: {int((score/q_count)*100)}점")
                    
                    else: # 동의어 시험
                        raw_df['DAY_NUM'] = raw_df['DAY'].astype(str).str.extract(r'(\d+)').fillna(1).astype(int)
                        filtered_df = raw_df[(raw_df['DAY_NUM'] >= config['start']) & (raw_df['DAY_NUM'] <= config['end'])]
                        
                        if len(filtered_df) == 0: st.error("범위 내 데이터 부족")
                        else:
                            q_count = min(30, len(filtered_df))
                            q_df = filtered_df.sample(n=q_count, random_state=42).reset_index(drop=True)
                            
                            # 동의어 컬럼 유연하게 매핑
                            syn_col = [c for c in raw_df.columns if '동의어' in c][0]
                            word_col = [c for c in raw_df.columns if '표제어' in c or 'word' in c or '단어' in c][0]
                            all_synonyms = raw_df[syn_col].dropna().unique().tolist()
                            
                            score = 0
                            for idx, row in q_df.iterrows():
                                target_word = str(row[word_col])
                                sentence = str(row['예문'])
                                if target_word and target_word in sentence:
                                    sentence = sentence.replace(target_word, f"<u><b>{target_word}</b></u>")
                                
                                st.markdown(f"##### Q{idx+1}. 다음 문맥상 밑줄 친 단어와 동의어를 고르시오.")
                                st.markdown(f"> {sentence}", unsafe_allow_html=True)
                                
                                correct = row[syn_col]
                                distractors = random.sample([s for s in all_synonyms if s != correct], min(3, len(all_synonyms)-1))
                                options = list(set([correct] + distractors))
                                random.shuffle(options)
                                ans = st.radio(f"선택 (Q{idx+1})", options, key=f"syn_{idx}", index=None)
                                if ans == correct: score += 1
                                st.divider()
                            if st.button("🎯 동의어 답안 제출"):
                                st.balloons()
                                st.success(f"💯 {s_name} 학생 제출 완료! 점수: {int((score/q_count)*100)}점")

elif menu == "🔒 관리자 대시보드":
    st.title("🔒 원장님 전용 관리자 제어 대시보드")
    pwd = st.text_input("관리자 비밀번호를 입력하세요:", type="password")
    
    if pwd == "1234":
        st.success("✅ 마스터 권한 인증 성공")
        tab1, tab2 = st.tabs(["📝 테스트 실시간 배포기", "📊 출결 및 통계"])
        with tab1:
            st.subheader("📢 오늘 시행할 단어 테스트 설정 및 배포")
            b_type = st.selectbox("1. 시험 유형 설정", ["뜻 맞추기", "동의어 문맥 빈칸"])
            book = st.selectbox("2. 대상 교재 지정", ["MVP1", "MVP2"])
            start_day, end_day = st.slider("3. 출제 진도 범위 지정 (DAY)", 1, 30, (1, 2))
            
            if st.button("🚀 즉시 시험 활성화 (학생 화면에 공개)"):
                st.session_state.test_active = True
                st.session_state.test_config = {"type": "뜻쓰기" if b_type == "뜻 맞추기" else "동의어", "book": book, "start": start_day, "end": end_day}
                st.success("📢 학생 전용 탭에 실시간 시험지가 연동되었습니다!")
            if st.button("🛑 현재 진행 중인 시험 강제 종료/마감"):
                st.session_state.test_active = False
                st.info("시험지가 회수되어 마감 처리되었습니다.")
