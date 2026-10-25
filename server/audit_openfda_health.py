"""
Pharmaco-Llama OpenFDA API SLA Healthcheck & Latency Auditor
Author: Md Mushfiqur Rahim (NIH-Certified in Clinical Pharmacology & Clinical Research)
"""

import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from openfda_engine import query_drug_label, query_offline_label
from main import app
from fastapi.testclient import TestClient

def audit_openfda_sla():
    print("=" * 65)
    print("[CLINICAL AUDIT] PHARMACO-LLAMA OPENFDA & SERVICE HEALTHCHECK")
    print("=" * 65)

    # 1. Test Live / Fallback OpenFDA API Latency
    print("[1/3] Auditing OpenFDA Query Performance...")
    t0 = time.perf_counter()
    res = query_drug_label("warfarin")
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0

    print(f" -> Query Target: Warfarin Sodium")
    print(f" -> Status: {res.get('status')}")
    print(f" -> Latency: {latency_ms:.2f} ms")
    
    # Assert valid clinical content
    assert "boxed_warning" in res, "Missing boxed_warning in OpenFDA response"
    assert len(res["boxed_warning"]) > 0, "Empty boxed_warning in response"
    print(f" -> Boxed Warning Verified: {res['boxed_warning'][0][:60]}...")

    # 2. Test Offline Zero-Latency Failover Engine
    print("\n[2/3] Auditing Local Ground-Truth Fallback Engine...")
    t0 = time.perf_counter()
    offline_res = query_offline_label("clopidogrel")
    t1 = time.perf_counter()
    offline_latency_ms = (t1 - t0) * 1000.0

    print(f" -> Query Target: Clopidogrel Bisulfate (Offline Cache)")
    print(f" -> Status: {offline_res.get('status')}")
    print(f" -> Offline Latency: {offline_latency_ms:.3f} ms (Target < 2.0 ms)")
    assert offline_latency_ms < 10.0, "Offline lookup exceeded latency threshold"
    assert "CYP2C19" in " ".join(offline_res.get("boxed_warning", [])), "Missing PGx warning in offline cache"

    # 3. Test FastAPI App /health Endpoint
    print("\n[3/3] Auditing FastAPI Service Health Endpoint...")
    client = TestClient(app)
    response = client.get("/health")
    print(f" -> Endpoint /health status code: {response.status_code}")
    assert response.status_code == 200, f"Healthcheck failed with code {response.status_code}"
    payload = response.json()
    print(f" -> Service: {payload.get('service')}")
    print(f" -> FDA Connectivity: {payload.get('fda_database')}")
    assert payload.get("status") == "healthy", "Service status is not healthy"

    print("\n" + "=" * 65)
    print("[SUCCESS] ALL CLINICAL CI AUDITS & SLA CHECKS PASSED SUCCESSFULLY")
    print("=" * 65)
    return True

if __name__ == "__main__":
    try:
        audit_openfda_sla()
        sys.exit(0)
    except Exception as e:
        print(f"\n[FAIL] HEALTHCHECK AUDIT FAILED: {str(e)}", file=sys.stderr)
        sys.exit(1)
