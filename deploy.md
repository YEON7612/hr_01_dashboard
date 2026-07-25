# 배포 가이드 (수강생용)

이 대시보드를 본인 GitHub·Streamlit Cloud 계정으로 그대로 배포하는 방법입니다.

## 1. 사전 준비

- GitHub 계정
- Streamlit Community Cloud 계정 (share.streamlit.io, GitHub 계정으로 로그인)

## 2. 로컬에서 실행해보기

```
pip install -r requirements.txt
streamlit run app.py
```

## 3. GitHub에 올리기

```
git init
git add .
git commit -m "Initial commit"
```

GitHub CLI가 있다면:
```
gh repo create <본인계정>/customer-churn-dashboard --public --source=. --remote=origin --push
```
없다면 GitHub 웹에서 새 저장소를 만들고 안내되는 명령어로 push하면 됩니다.

## 4. Streamlit Community Cloud 배포

1. https://share.streamlit.io 접속 → GitHub 계정으로 로그인
2. **"Create app"** → **"Deploy a public app from GitHub"**
3. Repository: `<본인계정>/customer-churn-dashboard`, Branch: `master`, Main file path: `app.py`
4. **Deploy 누르기 전에 "Advanced settings" 클릭 → Python version을 3.12로 선택** (중요, 아래 트러블슈팅 참고)
5. **Deploy**

## 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 배포 로그가 `Using Python 3.14.x environment`에서 멈추거나 매우 느림 | Streamlit Cloud가 강제하는 최신 Python과 `requirements.txt`의 구버전 패키지 간 wheel 미지원 | 앱 **삭제 후 재배포**하면서 Advanced settings에서 Python 3.12 선택 (`runtime.txt`는 현재 Streamlit 버그로 무시되니 반드시 이 화면에서 지정) |
| `ModuleNotFoundError: statsmodels` | `trendline="ols"`가 내부적으로 statsmodels를 쓰는데 requirements.txt에 빠짐 | `requirements.txt`에 `statsmodels==0.14.6` 추가 확인 |
