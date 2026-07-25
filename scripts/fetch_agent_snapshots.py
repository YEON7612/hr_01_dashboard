# -*- coding: utf-8 -*-
"""
"상담원 관점" 섹션이 쓰는 BigQuery 쿼리 두 개(상담원 단위, 상담 단위)를 실행해
data/agents_snapshot.csv, data/agent_consultations_snapshot.csv로 저장한다.
실행: python scripts/fetch_agent_snapshots.py  (사전에 gcloud auth application-default login 필요)
"""

import os
from google.cloud import bigquery

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

PROJECT = "project-b4df4ac8-b7ed-40e5-9af"
AGENTS_DATASET = "PROJECT1_DAY"
CONSULT_DATASET = "project1_day_03"

client = bigquery.Client(project=PROJECT)

agent_query = f"""
WITH agent_csat AS (
  SELECT c.agent_id, AVG(s.csat) AS avg_csat
  FROM `{PROJECT}.{CONSULT_DATASET}.consultations_table` c
  JOIN `{PROJECT}.{CONSULT_DATASET}.satisfaction_table` s ON c.consult_id = s.consult_id
  WHERE c.agent_id IS NOT NULL
  GROUP BY c.agent_id
)
SELECT a.agent_id, a.team, a.overtime_hours_avg, a.agent_satisfaction, ac.avg_csat
FROM `{PROJECT}.{AGENTS_DATASET}.agents01` a
JOIN agent_csat ac ON a.agent_id = ac.agent_id
"""

consult_query = f"""
SELECT c.agent_id, a.team, a.training_completed_yn, c.is_recontact, s.csat
FROM `{PROJECT}.{CONSULT_DATASET}.consultations_table` c
JOIN `{PROJECT}.{CONSULT_DATASET}.satisfaction_table` s ON c.consult_id = s.consult_id
JOIN `{PROJECT}.{AGENTS_DATASET}.agents01` a ON c.agent_id = a.agent_id
"""

agents_df = client.query(agent_query).result().to_dataframe()
consult_df = client.query(consult_query).result().to_dataframe()

agents_path = os.path.join(DATA_DIR, "agents_snapshot.csv")
consult_path = os.path.join(DATA_DIR, "agent_consultations_snapshot.csv")

agents_df.to_csv(agents_path, index=False, encoding="utf-8-sig")
consult_df.to_csv(consult_path, index=False, encoding="utf-8-sig")

print(f"agents_snapshot.csv: {len(agents_df)} rows -> {agents_path}")
print(f"agent_consultations_snapshot.csv: {len(consult_df)} rows -> {consult_path}")
