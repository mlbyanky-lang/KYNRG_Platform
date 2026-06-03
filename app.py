import streamlit as st
import pandas as pd
import random
import re
from datetime import datetime

st.set_page_config(page_title="김영편입 노량진 AI 통합 LMS", page_icon="🏫", layout="wide")

# ==========================================
# 0. 데이터 로드 엔진 (공백/대소문자 완벽 가드)
# ==========================================
@st.cache_data(ttl=60)
def load_data(file_type, book_choice):
    filename = f"{book_choice}_{file_type}.csv"
    try:
        df = pd.read_csv(filename, encoding='utf-8')
    except Exception:
        try:
            df = pd.read_csv(filename, encoding='utf-8-sig')
        except Exception:
            st.error(f"🚨 {filename} 파일을 시스템 내부에서 찾을 수 없습니다.")
            return pd.DataFrame()
            
    if not df.empty:
        try:
            # 컬럼명 양끝 공백 제거 및 소문자 정형화
            df.columns = df.columns.str.strip().str.lower()
            df = df.dropna(subset=['day'])
            df['day'] = pd.to_numeric(df['day'], errors='coerce').fillna(1).astype(int)
            df = df[df['day'] >= 1]
            return df.reset_index(drop=True)
        except Exception as e:
            st.error(f"🚨 데이터 가공 중 분석 오류 발생: {e}")
            return pd.DataFrame()
    return df

# ==========================================
# ⚙️ 편입 최적화 오답 메이커: 철자 유사 단어 추적기
# ==========================================
def get_similar_words(target_word, all_words_pool, count=3):
    target_word = str(target_word).strip().lower()
    if len(target_word) < 2:
        return random.sample(all_words_pool, min(count, len(all_words_pool)))
        
    prefix = target_word[:2]
    candidates = [w for w in all_words_pool if str(w).strip().lower().startswith(prefix) and str(w).strip().lower() != target_word]
    
    if len(candidates) < count:
        candidates += [w for w in all_words_pool if abs(len(str(w)) - len(target_word)) <= 2 and w not in candidates and str(w).strip().lower() != target_word]
        
    if len(candidates) < count:
        candidates += [w for w in all_words_pool if w not in candidates and str(w).strip().lower() != target_word]
        
    candidates = list(set([str(c).strip() for c in candidates if pd.notna(c) and str(c).strip() != ""]))
    return random.sample(candidates, min(count, len(candidates)))

# ==========================================
# 1. 시스템 전역 변수 및 세션 상태 초기화
# ==========================================
# 두 시험을 개별 제어하기 위해 상태 독립 분리
if "mean_test_active" not in st.session_state: st.session_state.mean_test_active = False
if "mean_test_config" not in st.session_state: st.session_state.mean_test_config = {}

if "syn_test_active" not in st.session_state: st.session_state.syn_test_active = False
if "syn_test_config" not in st.session_state: st.session_state.syn_test_config = {}

if "announcements" not in st.session_state:
    st.session_state.announcements = {
        "CLASS E": ["금일 모의고사 오답노트 점검이 야간 자습 1교시에 있습니다."],
        "CLASS C": ["데일리 테스트 누적 미통과자는 재시험 대상입니다."],
        "CLASS BD": ["단어 암기 미달자는 의무 자습 시간 연장됩니다."],
        "CLASS BJ": ["과제 제출 마감은 금일 오후 10시까지입니다."],
        "CLASS A": ["최상위권 특별 고난도 어휘 배포 자료를 수령하세요."]
    }

if "students_dict" not in st.session_state:
    st.session_state.students_dict = {
        "CLASS E": ["김철수", "이영희", "박민수", "최재성", "정지원"],
        "CLASS C": ["강동우", "조현아", "윤서준", "한지민", "배수지"],
        "CLASS BD": ["고윤정", "송중기", "이도현", "임지연", "박서준"],
        "CLASS BJ": ["차은우", "한소희", "장원영", "정국", "뷔"],
        "CLASS A": ["홍길동", "성춘향", "이몽룡", "심청", "임꺽정"]
    }
if "exam_results" not in st.session_state: st.session_state.exam_results = []
if "exam_started" not in st.session_state: st.session_state.exam_started = False
if "current_questions" not in st.session_state: st.session_state.current_questions = []
if "current_exam_type" not in st.session_state: st.session_state.current_exam_type = ""

# ==========================================
# 2. 사이드바 네비게이션 (이원화 메뉴 반영)
# ==========================================
st.sidebar.title("🏫 김영편입 노량진")
menu = st.sidebar.radio("📌 시스템 메뉴 선택", [
    "📢 반별 공지사항", 
    "📖 데일리 암기장", 
    "📝 실전 뜻찾기 테스트", 
    "📝 실전 동의어 테스트", 
    "🔒 원장님 전용 대시보드"
])
st.sidebar.divider()
st.sidebar.caption("© 2026 김영편입 AI 학습 관리 시스템")

# ==========================================
# 3. 메뉴별 기능 완벽 구현
# ==========================================

if menu == "📢 반별 공지사항":
    st.title("📢 반별 학습 공지사항")
    student_class = st.selectbox("본인의 소속 반을 선택하세요:", list(st.session_state.students_dict.keys()))
    st.subheader(f"✨ {student_class} 오늘의 공지 목록")
    notices = st.session_state.announcements.get(student_class, [])
    if notices:
        for idx, notice in enumerate(notices):
            st.info(f"📌 **[{idx+1}]** {notice}")
    else:
        st.write("현재 등록된 공지사항이 없습니다.")

elif menu == "📖 데일리 암기장":
    st.title("📖 데일리 플래시 암기장")
    col1, col2 = st.columns(2)
    with col1: book_choice = st.selectbox("📚 단어 교재 선택:", ["MVP1", "MVP2"])
    
    df = load_data("뜻쓰기", book_choice)
    if not df.empty:
        days = sorted(df['day'].unique())
        with col2: target_day = st.selectbox("📅 진도 DAY 선택:", [f"DAY {d:02d}" for d in days])
        
        target_num = int(target_day.split()[1])
        day_df = df[df['day'] == target_num].reset_index(drop=True)
        
        st.success(f"🔥 {book_choice} - {target_day} 어휘 목록 (총 {len(day_df)}개 단어)")
        st.dataframe(day_df[['word', 'meaning']], use_container_width=True)

# --- [개편 메뉴 2] 실전 뜻찾기 테스트 ---
elif menu == "📝 실전 뜻찾기 테스트":
    st.title("📝 실전 뜻찾기 데일리 테스트")
    
    if not st.session_state.mean_test_active:
        st.warning("🔒 현재 활성화된 뜻찾기 시험이 없습니다. 원장님이 시험을 출제할 때까지 대기해 주세요.")
    else:
        config = st.session_state.mean_test_config
        st.info(f"🎯 **뜻찾기 활성 시험:** {config['book']} | **범위:** DAY {config['start']} ~ {config['end']} ({config['num_q']}문항)")
        
        col1, col2 = st.columns(2)
        with col1: s_class = st.selectbox("소속 반 선택:", list(st.session_state.students_dict.keys()), key="mean_class")
        with col2: s_name = st.selectbox("본인 이름 선택:", st.session_state.students_dict[s_class], key="mean_name")
        
        if not st.session_state.exam_started:
            if st.button("🚀 뜻찾기 시험 시작", use_container_width=True):
                raw_df = load_data("뜻쓰기", config['book'])
                if not raw_df.empty:
                    filtered_df = raw_df[(raw_df['day'] >= config['start']) & (raw_df['day'] <= config['end'])]
                    
                    if len(filtered_df) == 0:
                        st.error("지정 범위 내에 단어 데이터가 부족합니다.")
                    else:
                        unique_words = filtered_df['word'].drop_duplicates().tolist()
                        random.shuffle(unique_words)
                        q_count = min(config['num_q'], len(unique_words))
                        target_words = unique_words[:q_count]
                        
                        sampled_df = pd.concat([filtered_df[filtered_df['word'] == w].sample(n=1) for w in target_words]).reset_index(drop=True)
                        all_meanings = list(raw_df['meaning'].dropna().str.strip().unique())
                        
                        questions = []
                        for _, row in sampled_df.iterrows():
                            correct = str(row['meaning']).strip()
                            wrong_pool = [m for m in all_meanings if m != correct]
                            wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))
                            options = [correct] + wrong
                            random.shuffle(options)
                            questions.append({
                                'title': f"`{row['word']}` 의 뜻으로 가장 알맞은 것은?",
                                'context': None,
                                'options': options,
                                'correct': correct
                            })
                        
                        st.session_state.current_questions = questions
                        st.session_state.current_exam_type = "뜻찾기"
                        st.session_state.exam_started = True
                        st.rerun()
                        
        if st.session_state.exam_started and st.session_state.current_exam_type == "뜻찾기":
            st.subheader(f"✍️ {s_name} 학생의 뜻찾기 시험지")
            with st.form("mean_exam_form"):
                student_answers = []
                for i, q in enumerate(st.session_state.current_questions):
                    st.markdown(f"##### **[Q{i+1}]** {q['title']}")
                    user_ans = st.radio(f"보기 선택 (Q{i+1})", q['options'], key=f"mean_ans_{i}", index=None, label_visibility="collapsed")
                    student_answers.append(user_ans)
                    st.divider()
                
                if st.form_submit_button("🎯 최종 답안 제출 및 자동 채점"):
                    if None in student_answers:
                        st.warning("⚠️ 풀지 않은 문항이 있습니다. 모든 문제의 답을 체크해 주세요.")
                    else:
                        correct_count = sum([1 for u_a, q in zip(student_answers, st.session_state.current_questions) if u_a == q['correct']])
                        score = int((correct_count / len(student_answers)) * 100)
                        
                        st.session_state.exam_results.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "class": s_class, "name": s_name, "type": "뜻찾기",
                            "test_name": f"{config['book']}_DAY{config['start']}~{config['end']}", "score": score
                        })
                        st.balloons()
                        st.success(f"💯 제출 완료! {s_name} 학생의 점수는 **{score}점**입니다.")
                        st.session_state.exam_started = False
                        st.session_state.current_questions = []

# --- [개편 메뉴 3] 실전 동의어 테스트 ---
elif menu == "📝 실전 동의어 테스트":
    st.title("📝 실전 동의어 문맥 추론 테스트")
    
    if not st.session_state.syn_test_active:
        st.warning("🔒 현재 활성화된 동의어 문맥 시험이 없습니다. 원장님이 시험을 출제할 때까지 대기해 주세요.")
    else:
        config = st.session_state.syn_test_config
        st.info(f"🎯 **동의어 활성 시험:** {config['book']} | **범위:** DAY {config['start']} ~ {config['end']} ({config['num_q']}문항)")
        
        col1, col2 = st.columns(2)
        with col1: s_class = st.selectbox("소속 반 선택:", list(st.session_state.students_dict.keys()), key="syn_class")
        with col2: s_name = str(st.selectbox("본인 이름 선택:", st.session_state.students_dict[s_class], key="syn_name"))
        
        if not st.session_state.exam_started:
            if st.button("🚀 동의어 문맥 시험 시작", use_container_width=True):
                raw_df = load_data("동의어", config['book'])
                if not raw_df.empty:
                    filtered_df = raw_df[(raw_df['day'] >= config['start']) & (raw_df['day'] <= config['end'])]
                    
                    if len(filtered_df) == 0:
                        st.error("지정 범위 내에 단어 데이터가 부족합니다.")
                    else:
                        # 버그 제로 필터링: 중복 표제어 단어 원천 제거
                        unique_words = filtered_df['word'].drop_duplicates().tolist()
                        random.shuffle(unique_words)
                        q_count = min(config['num_q'], len(unique_words))
                        target_words = unique_words[:q_count]
                        
                        sampled_df = pd.concat([filtered_df[filtered_df['word'] == w].sample(n=1) for w in target_words]).reset_index(drop=True)
                        
                        # 💡 [버그 대도려내기] 정형화된 이름으로 매칭 컬럼 추적
                        syn_cols = [c for c in raw_df.columns if 'synonym' in c]
                        all_words_pool = list(raw_df['word'].dropna().str.strip().unique())
                        
                        questions = []
                        for _, row in sampled_df.iterrows():
                            # 유효 동의어 바인딩
                            row_syns = []
                            for col in syn_cols:
                                if col in row and pd.notna(row[col]) and str(row[col]).strip() != "":
                                    row_syns.append(str(row[col]).strip())
                            
                            if not row_syns: row_syns = [str(row['word'])]
                            
                            # 정답 무작위 1개 선정
                            correct = random.choice(row_syns)
                            # 원장님 표 철자 유사 오답 매칭
                            wrong = get_similar_words(correct, all_words_pool, count=3)
                            
                            options = [correct] + wrong
                            random.shuffle(options)
                            
                            # 하이라이트 문맥 가공
                            word = str(row['word']).strip()
                            sentence = str(row['example sentence'] if 'example sentence' in row else row['example_sentence']).strip()
                            highlighted_sentence = re.sub(f"({re.escape(word)})", r"<u><b>\1</b></u>", sentence, flags=re.IGNORECASE)
                            
                            questions.append({
                                'title': f"다음 문장의 밑줄 친 단어와 **가장 문맥상 뜻이 가까운 동의어**를 고르시오.",
                                'context': highlighted_sentence,
                                'options': options,
                                'correct': correct
                            })
                        
                        st.session_state.current_questions = questions
                        st.session_state.current_exam_type = "동의어"
                        st.session_state.exam_started = True
                        st.rerun()
                        
        if st.session_state.exam_started and st.session_state.current_exam_type == "동의어":
            st.subheader(f"✍️ {s_name} 학생의 동의어 문맥 시험지")
            with st.form("syn_exam_form"):
                student_answers = []
                for i, q in enumerate(st.session_state.current_questions):
                    st.markdown(f"##### **[Q{i+1}]** {q['title']}")
                    st.markdown(f"> {q['context']}", unsafe_allow_html=True)
                    user_ans = st.radio(f"보기 선택 (Q{i+1})", q['options'], key=f"syn_ans_{i}", index=None, label_visibility="collapsed")
                    student_answers.append(user_ans)
                    st.divider()
                
                if st.form_submit_button("🎯 최종 답안 제출 및 자동 채점"):
                    if None in student_answers:
                        st.warning("⚠️ 풀지 않은 문항이 있습니다. 모든 문제의 답을 체크해 주세요.")
                    else:
                        correct_count = sum([1 for u_a, q in zip(student_answers, st.session_state.current_questions) if u_a == q['correct']])
                        score = int((correct_count / len(student_answers)) * 100)
                        
                        st.session_state.exam_results.append({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "class": s_class, "name": s_name, "type": "동의어",
                            "test_name": f"{config['book']}_DAY{config['start']}~{config['end']}", "score": score
                        })
                        st.balloons()
                        st.success(f"💯 제출 완료! 점수: **{score}점**")
                        st.session_state.exam_started = False
                        st.session_state.current_questions = []

# --- [메뉴 4] 원장님 전용 대시보드 (분리 제어판 적용) ---
elif menu == "🔒 원장님 전용 대시보드":
    st.title("🔒 원장님 전용 통합 관리 시스템")
    if "admin_authenticated" not in st.session_state: st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        admin_pw = st.text_input("원장님 마스터 비밀번호를 입력하세요:", type="password")
        if st.button("로그인"):
            if admin_pw == "1234":
                st.session_state.admin_authenticated = True
                st.rerun()
            else: st.error("비밀번호가 일치하지 않습니다.")
    else:
        if st.button("🔓 로그아웃"):
            st.session_state.admin_authenticated = False
            st.rerun()
            
        tab1, tab2, tab3 = st.tabs(["📝 테스트 개별 배포 제어기", "📊 실시간 성적 및 미응시생 파악", "👨‍🎓 학생 명부 & 공지 제어"])
        
        # Tab 1: 독립 배포기
        with tab1:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("🅰️ 뜻찾기 테스트 실시간 설정")
                m_book = st.selectbox("교재 선택 (뜻)", ["MVP1", "MVP2"])
                m_start, m_end = st.slider("진도 범위 (뜻 DAY)", 1, 60, (1, 10), key="m_slide")
                m_num = st.number_input("출제 문항 수 (뜻)", min_value=5, max_value=100, value=20, step=5, key="m_num")
                if st.button("🚀 뜻찾기 시험 배포/활성화", use_container_width=True):
                    st.session_state.mean_test_active = True
                    st.session_state.mean_test_config = {"book": m_book, "start": m_start, "end": m_end, "num_q": m_num}
                    st.success("뜻찾기 시험지가 오픈되었습니다.")
                if st.button("🛑 뜻찾기 시험 마감/종료", use_container_width=True):
                    st.session_state.mean_test_active = False
                    st.info("뜻찾기 시험이 마감되었습니다.")
                    
            with col2:
                st.subheader("🅱️ 동의어 문맥 테스트 실시간 설정")
                s_book = st.selectbox("교재 선택 (동의어)", ["MVP1", "MVP2"])
                s_start, s_end = st.slider("진도 범위 (동의어 DAY)", 1, 60, (1, 10), key="s_slide")
                s_num = st.number_input("출제 문항 수 (동의어)", min_value=5, max_value=100, value=20, step=5, key="s_num")
                if st.button("🚀 동의어 테스트 배포/활성화", use_container_width=True):
                    st.session_state.syn_test_active = True
                    st.session_state.syn_test_config = {"book": s_book, "start": s_start, "end": s_end, "num_q": s_num}
                    st.success("동의어 문맥 시험지가 오픈되었습니다.")
                if st.button("🛑 동의어 테스트 마감/종료", use_container_width=True):
                    st.session_state.syn_test_active = False
                    st.info("동의어 시험이 마감되었습니다.")
        
        # Tab 2: 미응시자 및 집계 분리
        with tab2:
            st.subheader("📈 실시간 성적 분석 및 시험별 미응시생 파악")
            if not st.session_state.exam_results:
                st.info("아직 제출된 시험 데이터가 없습니다.")
            else:
                res_df = pd.DataFrame(st.session_state.exam_results)
                st.dataframe(res_df, use_container_width=True)
                
                # 미응시자 분리 색출
                st.divider()
                st.markdown("#### **🚨 반별/시험 종류별 실시간 미응시자 실시간 추적**")
                chk_class = st.selectbox("조회할 반 선택:", list(st.session_state.students_dict.keys()))
                chk_type = st.radio("조회할 시험 유형 선택:", ["뜻찾기", "동의어"])
                
                all_studs = st.session_state.students_dict[chk_class]
                done_studs = res_df[(res_df['class'] == chk_class) & (res_df['type'] == chk_type)]['name'].tolist()
                not_done = [s for s in all_studs if s not in done_studs]
                
                if not_done:
                    st.error(f"❌ **{chk_class} - {chk_type} 미응시 학생 ({len(not_done)}명):** {', '.join(not_done)}")
                else:
                    st.success(f"✅ **{chk_class} 반은 현재 {chk_type} 시험을 전원 응시 완료했습니다!**")
                
                csv_data = res_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 전체 성적 엑셀 마스터 다운로드", data=csv_data, file_name="Noryangjin_LMS_Results.csv", mime="text/csv")
        
        # Tab 3: 명부 제어
        with tab3:
            c_choice = st.selectbox("관리할 반 선택:", list(st.session_state.students_dict.keys()), key="tab3_class")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**[{c_choice}] 학생 명부 편집**")
                current_students_str = "\n".join(st.session_state.students_dict[c_choice])
                new_students_str = st.text_area("이름을 한 줄에 한 명씩 입력:", value=current_students_str, height=150)
                if st.button(f"💾 {c_choice} 명부 저장"):
                    st.session_state.students_dict[c_choice] = [name.strip() for name in new_students_str.split("\n") if name.strip()]
                    st.success("명부가 업데이트되었습니다.")
            with col2:
                st.markdown(f"**[{c_choice}] 새로운 실시간 공지 등록**")
                new_notice = st.text_input("공지 내용:")
                if st.button(f"📢 {c_choice} 공지 발행"):
                    if new_notice.strip():
                        st.session_state.announcements[c_choice].insert(0, new_notice.strip())
                        st.success("공지가 실시간 반영되었습니다.")
