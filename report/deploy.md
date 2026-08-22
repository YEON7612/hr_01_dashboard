# 🚀 대시보드 배포 및 데이터 폴백(Fallback) 가이드

## 1. 개요 및 구조
* **로컬 환경**: 내 컴퓨터의 GCP 인증 정보(ADC)로 BigQuery 라이브 조회가 가능합니다.
* **배포 환경 (Streamlit Cloud)**: 인증 정보가 없어도 앱이 멈추지 않도록 `data/` 폴더의 스냅샷 CSV를 자동으로 불러옵니다.

## 2. 배포 단계
1. **깃허브 올리기**: `data/*.csv` 스냅샷 파일이 `.gitignore`에 걸리지 않았는지 확인 후 Push합니다.
2. **Streamlit Cloud 연결**: Repository와 `app.py` 경로를 지정하여 배포합니다.
3. **Secrets 등록 (선택)**: Streamlit Cloud Settings > Secrets에 `gcp_service_account` 키를 등록하면 배포 환경에서도 BigQuery 라이브 조회가 가능합니다.

## 3. 자주 겪는 문제 및 해결법
| 현상 | 원인 | 해결책 |
| :--- | :--- | :--- |
| `FileNotFoundError` | CSV 스냅샷 파일이 깃허브에 안 올라감 | `git add -f data/*.csv` 명령어로 강제 추가 후 push |
| 배포 후 화면에 에러 발생 | BigQuery 인증 실패 시 예외 처리 누락 | `app.py` 내 `try-except` 폴백 로직 확인 |