import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="김영편입 AI 통합 관리 시스템", page_icon="🏫", layout="wide")

# ==========================================
# 0. 깃허브 업로드 파일 연동 엔진
# ==========================================
@st.cache_data
def load_data(file_type, book_choice):
    try:
        if file_type == "뜻쓰기":
            # 원장님 파일명: MVP1.csv, MVP2.csv
            df = pd.read_csv(f"{book_choice}.csv")
            # 대소문자 섞인 day 컬럼 통일
            if 'day' in df.columns: df.rename(columns={'day': 'DAY'}, inplace=True)
            if 'day ' in df.columns: df.rename(columns={'day ': 'DAY'}, inplace=True)
            return df
        else:
            # 원장님 파일명: MVP1예문(Day1_60)_작업.xlsx - Vol.1 Day 1~30.csv
            filename = f"{book_choice}예문(Day1_60)_작업.xlsx - Vol.1 Day 1~30.csv"
            df = pd.read_csv(filename)
            if '데이' in df.columns: df.rename(columns={'데이': 'DAY'}, inplace=True)
            return df
    except Exception as e:
        st.error(f"🚨 {book_choice} {file_type} 파일을 읽어오지 못했습니다. 파일명을 확인해 주세요.")
        st.info(f"상세 원인: {e}")
        return pd.DataFrame()

# 임시 세션 상태 초기화 (출제 세팅용)
if "test_active" not in st.session_state:
    st.session_state.test_active = False
if "test_config" not in st.session_state:
    st.session_state.test_config = {}

# ==========================================
# 1. 사이드바 네비게이션
# ==========================================
st.sidebar.title("🏫 김영편입 노량진")
menu = st.sidebar.radio("📌 메뉴 이동", [
    "📢 반별 공지사항", 
    "📖 데일리 암기장", 
    "📝 실전 단어 테스트",
    "🔒 관리자 대시보드"
])
st.sidebar.divider()
st.sidebar.caption("© 2026 김영편입 노량진 AI LMS")

# ==========================================
# 2. 메뉴별 화면 구현
# ==========================================

# --- [메뉴 1] 반별 공지사항 ---
if menu == "📢 반별 공지사항":
    st.title("📢 반별 공지사항 및 안내")
    student_class = st.selectbox("소속 반을 선택하세요:", ["CLASS E", "CLASS C", "CLASS BD", "CLASS BJ", "CLASS A"])
    st.success(f"**{student_class}** 학생들을 위한 오늘의 공지입니다.")
    
    # 예시 공지 (향후 관리자 페이지와 연동)
    st.info("🔥 [필독] 금일 데일리 테스트 미응시자는 야간 자습 전 재시험이 배정됩니다. 반드시 제한 시간 내에 응시하세요!")

# --- [메뉴 2] 데일리 암기장 ---
elif menu == "📖 데일리 암기장":
    st.title("📖 데일리 암기 플래시카드")
    col1, col2 = st.columns(2)
    with col1: book_choice = st.selectbox("📚 교재 선택:", ["MVP1", "MVP2"])
    
    df = load_data("뜻쓰기", book_choice)
    if not df.empty:
        # 가공: DAY 값 숫자만 추출해서 정렬용 리스트업
        df['DAY_NUM'] = df['DAY'].astype(str).str.extract(r'(\d+)').astype(int)
        days = sorted(df['DAY_NUM'].unique())
        
        with col2:
            target_day = st.selectbox("📅 학습할 DAY 선택:", [f"DAY {d:02d}" for d in days])
        
        target_num = int(target_day.split()[1])
        day_df = df[df['DAY_NUM'] == target_num]
        
        st.subheader(f"✨ {book_choice} - {target_day} 학습 단어 (총 {len(day_df)}개)")
        st.dataframe(day_df[['word', 'meaning']].reset_index(drop=True), use_container_width=True)

# --- [메뉴 3] 실전 단어 테스트 ---
elif menu == "📝 실전 단어 테스트":
    st.title("📝 실전 데일리 테스트")
    
    if not st.session_state.test_active:
        st.warning("🔒 현재 활성화된 시험이 없습니다. 원장님이 관리자 대시보드에서 시험을 출제할 때까지 기다려주세요.")
    else:
        config = st.session_state.test_config
        st.info(f"🎯 오늘의 시험: **{config['book']} ({config['type']})** | 범위: **DAY {config['start']} ~ {config['end']}**")
        
        # 학생 정보 입력
        s_class = st.selectbox("본인의 반을 선택하세요:", ["CLASS E", "CLASS C", "CLASS BD", "CLASS BJ", "CLASS A"])
        s_name = st.text_input("이름을 입력하세요:")
        
        if s_name:
            if st.button("🚀 시험지 생성 및 시작"):
                st.session_state.start_exam = True
                
            if "start_exam" in st.session_state and st.session_state.start_exam:
                st.divider()
                # 데이터 로드
                raw_df = load_data(config['type'], config['book'])
                
                if not raw_df.empty:
                    # 범위 필터링
                    if config['type'] == "뜻쓰기":
                        raw_df['DAY_NUM'] = raw_df['DAY'].astype(str).str.extract(r'(\d+)').astype(int)
                        filtered_df = raw_df[(raw_df['DAY_NUM'] >= config['start']) & (raw_df['DAY_NUM'] <= config['end'])]
                        
                        if len(filtered_df) == 0:
                            st.error("해당 범위에 데이터가 없습니다.")
                        else:
                            # 50문제 추출 (모자라면 전체)
                            q_count = min(50, len(filtered_df))
                            q_df = filtered_df.sample(n=q_count, random_state=42).reset_index(drop=True)
                            all_meanings = raw_df['meaning'].dropna().unique().tolist()
                            
                            student_answers = []
                            score = 0
                            
                            # 시험지 표출
                            for idx, row in q_df.iterrows():
                                st.markdown(f"#### Q{idx+1}. `{row['word']}` 의 뜻으로 알맞은 것은?")
                                correct = row['meaning']
                                # 오답 3개 섞기
                                distractors = random.sample([m for m in all_meanings if m != correct], 3)
                                options = [correct] + distractors
                                random.shuffle(options)
                                
                                ans = st.radio(f"선택지 (Q{idx+1})", options, key=f"q_{idx}", index=None)
                                student_answers.append((ans, correct))
                            
                            if st.button("🎯 최종 답안 제출"):
                                for ans, correct in student_answers:
                                    if ans == correct: score += 1
                                total_score = int((score / q_count) * 100)
                                st.balloons()
                                st.success(f"💯 {s_name} 학생의 시험이 끝났습니다! 점수: {total_score}점 / 100점")
                                # 성적 결과 처리 로직 (나중에 엑셀 누적 등 연동)
                                
                    else: # 동의어 시험인 경우
                        raw_df['DAY_NUM'] = raw_df['DAY'].astype(int)
                        filtered_df = raw_df[(raw_df['DAY_NUM'] >= config['start']) & (raw_df['DAY_NUM'] <= config['end'])]
                        
                        if len(filtered_df) == 0:
                            st.error("해당 범위에 데이터가 없습니다.")
                        else:
                            q_count = min(30, len(filtered_df)) # 동의어는 30문제 기준
                            q_df = filtered_df.sample(n=q_count, random_state=42).reset_index(drop=True)
                            all_synonyms = raw_df['동의어 1'].dropna().unique().tolist()
                            
                            score = 0
                            for idx, row in q_df.iterrows():
                                # 문맥 동의어 예문 가공 (PDF처럼 밑줄 표시 시각화)
                                target_word = row['표제어'] if '표제어' in raw_df.columns else ""
                                sentence = str(row['예문'])
                                if target_word and target_word in sentence:
                                    sentence = sentence.replace(target_word, f"<u><b>{target_word}</b></u>")
                                
                                st.markdown(f"#### Q{idx+1}. 다음 문장의 밑줄 친 단어와 **가장 뜻이 가까운 것**을 고르시오.")
                                st.markdown(f"> {sentence}", unsafe_allow_html=True)
                                
                                correct = row['동의어 1']
                                distractors = random.sample([s for s in all_synonyms if s != correct], 3)
                                options = [correct] + distractors
                                random.shuffle(options)
                                
                                ans = st.radio(f"선택지 (Q{idx+1})", options, key=f"syn_{idx}", index=None)
                                if ans == correct: score += 1
                                
                            if st.button("🎯 동의어 답안 제출"):
                                total_score = int((score / q_count) * 100)
                                st.balloons()
                                st.success(f"💯 {s_name} 학생 제출 완료! 점수: {total_score}점")

# --- [메뉴 4] 관리자 대시보드 ---
elif menu == "🔒 관리자 대시보드":
    st.title("🔒 원장님 전용 관리자 대시보드")
    pwd = st.text_input("관리자 비밀번호를 입력하세요:", type="password")
    
    if pwd == "1234":
        st.success("✅ 인증 성공. 학원 전용 제어 시스템이 활성화되었습니다.")
        
        tab1, tab2 = st.tabs(["📝 실시간 데일리 테스트 출제기", "📊 학생 통계 및 미응시생 확인"])
        
        with tab1:
            st.subheader("📢 오늘 진행할 데일리 테스트 설정")
            b_type = st.selectbox("1. 출제할 시험 종류 선택", ["뜻 맞추기", "동의어 문맥 빈칸"])
            book = st.selectbox("2. 출제 교재 선택", ["MVP1", "MVP2"])
            
            start_day, end_day = st.slider("3. 출제 DAY 범위 지정 (슬라이더 조절)", 1, 30, (1, 2))
            
            if st.button("🚀 위 조건으로 학생들에게 시험 배포/공개"):
                st.session_state.test_active = True
                st.session_state.test_config = {
                    "type": "뜻쓰기" if b_type == "뜻쓰기" else "동의어",
                    "book": book,
                    "start": start_day,
                    "end": end_day
                }
                st.success(f"📢 완료! 이제 학생들이 [📝 실전 단어 테스트] 메뉴에 접속하면 {book} DAY {start_day}~{end_day} 시험을 풀 수 있습니다!")
                
            if st.button("🛑 현재 진행 중인 시험 마감/종료"):
                st.session_state.test_active = False
                st.info("시험이 마감되어 학생들이 더 이상 풀 수 없습니다.")
                
        with tab2:
            st.subheader("📈 반별 평균 및 미응시자 명단 추출")
            st.info("학생들이 실전 테스트를 완료하면 이곳에 반별 평균 점수(CLASS E, C 등)와 미응시자 리스트가 실시간 집계되어 도표로 나타납니다.")
            
    elif pwd:
        st.error("비밀번호가 일치하지 않습니다.")
