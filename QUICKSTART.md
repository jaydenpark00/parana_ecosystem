# 🚀 Quick Start Guide

**새로운 깔끔한 프로젝트입니다!**

---

## 📋 5분 안에 시작하기

### Step 1: 라이브러리 설치 (1분)

```bash
pip install -r requirements.txt
```

### Step 2: 분석 실행 (3분)

```bash
python run_analysis.py
```

### Step 3: 결과 확인 (1분)

```bash
# 생성된 파일 확인
dir outputs\v5_2

# 또는 파일 탐색기에서 보기
# outputs/v5_2/ 폴더에 결과 저장됨
```

---

## 📊 결과 파일

실행 후 `outputs/v5_2/` 폴더에 생성됨:

| 파일 | 내용 |
|------|------|
| `fig1_*.png` | 알고리즘 성능 비교 |
| `fig2_*.png` | 생존곡선 분석 |
| `fig3_*.png` | AUC/R50 분석 |
| `fig4_*.png` | 확장 분석 |
| `fig5_*.png` | 민감도 분석 |
| `*_ranking_*.csv` | 종 순위 |
| `performance_*.csv` | 성능 지표 |
| `sensitivity_*.csv` | 민감도 데이터 |

---

## ⚙️ 커스텀 설정

### theta 값 변경
```bash
# threshold 조정 (작을수록 연쇄 멸종 많음)
python run_analysis.py --theta 0.5
```

### 무작위 반복 횟수
```bash
# 기본 100번 → 50번으로 줄임 (빠름)
python run_analysis.py --random-repeats 50
```

### 출력 폴더
```bash
# 기본 outputs/v5_2 → custom_folder로 변경
python run_analysis.py --outdir custom_folder
```

---

## 📁 프로젝트 구조

```
new_project/
├─ README.md           ← 상세 문서 (읽어보세요!)
├─ QUICKSTART.md       ← 이 파일
├─ requirements.txt    ← 라이브러리 설정
├─ .gitignore         ← Git 설정
├─ run_analysis.py    ← 메인 스크립트 (실행 파일)
│
├─ data/              ← 데이터 (필수)
│  ├─ FW_001.csv      ← 40×36 식이 행렬 (핵심!)
│  ├─ parana_edgelist.csv
│  └─ generate_edgelist.py
│
├─ src/               ← 알고리즘 (12개 모듈)
│  ├─ wtecm.py        ← WTECM + Kosaraju
│  ├─ visualization.py ← 그림 생성
│  ├─ metrics.py      ← 지표 계산
│  ├─ scc.py          ← SCC 검증
│  └─ 기타 알고리즘들
│
└─ outputs/           ← 결과 저장 (자동 생성)
   └─ v5_2/           ← 최신 결과
```

---

## 🎯 핵심 개념 (30초 이해)

### 문제
```
Parana 강의 식이 네트워크에서
가장 중요한 물고기 종은 무엇인가?
```

### 해결책
```
WTECM: 한 종을 제거 → 몇 종이 연쇄 멸종되는가?
      → 더 많이 연쇄 멸종될수록 더 중요한 종!
```

### 검증
```
5가지 알고리즘 (Kosaraju, BC, CI, CoreHD)이
WTECM 결과와 얼마나 잘 맞는가?
```

---

## 🔍 세부 사항

### 데이터 형식
```
FW_001.csv: 40행 × 36열
- 행: 먹이 (물고기, 식물, 동물)
- 열: 포식자 (물고기만)
- 값: 각 포식자의 먹이 비중 (합=1.0)
```

### 실행 시간
```
전체: ~2-3분
├─ 데이터 처리: ~1초
├─ 5 알고리즘: ~1초
├─ 성능 평가: ~10초
└─ 시각화: ~30초
```

### 출력 결과
```
• PNG 이미지 5장 (성능 비교/분석)
• CSV 파일 4개 (데이터 저장)
• 총 크기: ~2MB
```

---

## ❓ 자주 묻는 질문

**Q: 데이터를 변경할 수 있나요?**
- A: 네! `data/FW_001.csv`를 새 40×36 행렬로 교체하면 됩니다.

**Q: 알고리즘을 추가할 수 있나요?**
- A: 네! `src/wtecm.py`의 `make_algorithm_rankings()` 함수를 수정하면 됩니다.

**Q: 결과를 다시 뽑으려면?**
- A: `outputs/v5_2` 폴더를 비운 후 다시 실행하면 됩니다.

**Q: 한글이 깨져요.**
- A: `pip install koreanize-matplotlib`를 다시 실행하세요.

---

## 🚀 다음 단계

1. **README.md** 읽기 (상세 문서)
2. **run_analysis.py** 실행하기
3. **outputs/v5_2/** 결과 확인하기
4. 필요하면 코드 커스터마이징

---

**준비 완료! 이제 실행하세요!** 🎉

```bash
python run_analysis.py
```
