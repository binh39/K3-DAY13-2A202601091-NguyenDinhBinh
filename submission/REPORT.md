# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm: _F1 Speed_
- Repository URL: https://github.com/binh39/K3-DAY13-2A202601091-NguyenDinhBinh
- Commit SHA cuối: 4b8bbfe (cập nhật sau khi commit phần QA/Report của người E)
- Thành viên và vai trò:
  - Đồng Đại Huy (2A202601901) — API & Middleware: triển khai CP1 Middleware, gán Correlation ID và bổ sung exception handler mở rộng.
  - Phạm Đức Trung (2A202601253) — Security Engineer: triển khai PII scrubbing, mở rộng regex PII và kiểm chứng log không lộ dữ liệu nhạy cảm.
  - Nguyễn Đình Bình (2A202601091) — SRE & Alerts Engineer: thiết lập SLO, viết alert rules symptom-based và runbook điều tra/giảm thiểu sự cố.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 100/100 (xác minh lại ngày 2026-08-11; ban đầu chỉ 30/100 ở baseline CP0, sau khi hoàn thiện correlation ID, enrichment và PII scrubbing)
- Tổng số traces: 15 traces `/chat` đã sinh trong các phiên load test (10 baseline + 5 challenge); con số trên Langfuse cũng có thể cao hơn nếu có thêm request kiểm thử thủ công — xác nhận số chính xác trên giao diện Langfuse.
- Số PII leak còn lại: 0 (`grep "@"` = 0, `grep "4111"` = 0; validator báo 0 leak; chỉ có chuỗi `[REDACTED_*]`)
- Link/đường dẫn dashboard: `config/dashboard.yaml` + `scripts/build_dashboard.py`; evidence tại `submission/evidence/scrdashboard.png` và `validate_dashboard_output.txt`

## 3. Logging và tracing

- Evidence correlation ID: `submission/evidence/cp1-logs.jsonl` — mọi log đều có `correlation_id` dạng `req-<8hex>` (vd `req-7ae539cf`, `req-4930678c`); kết quả `submission/evidence/validate-logs.txt` ghi 10 unique correlation ID, 0 lỗi.
- Evidence PII redaction: log chứa `[REDACTED_EMAIL]` thay cho email, không có `@` hay `4111` lọt log; validator báo `Potential PII leaks detected: 0`. Xem `submission/evidence/cp1-logs.jsonl`.
- Evidence trace waterfall: `submission/evidence/cp3-trace-waterfall.png` — span `run` lồng `retrieve` (RAG) và `generate` (LLM) nhờ decorator `@observe(as_type="span")` (phần mở rộng người E). Danh sách ≥10 trace chụp từ giao diện Langfuse: `submission/evidence/screenshot-traces.png`.
- Giải thích một span đáng chú ý: span `retrieve` trong incident `rag_slow` chiếm ~3.5s/3.7s tổng latency của `run` (span `generate` chỉ ~0.15s). Waterfall tách được RAG vs LLM giúp khoanh vùng nhanh root cause ở tầng retrieval.

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel có trong dashboard contract. (xem `submission/evidence/validate_dashboard_output.txt`)
- Evidence dashboard: `submission/evidence/scrdashboard.png` (đủ 6 panel: latency, traffic, errors, cost, tokens, quality — tên panel + time range hiển thị rõ, cả 6 panel đều OK: latency P95=151ms, traffic 10 req/phút, error_rate_pct=0.00% (0/10), cost $0.0181, tokens 330 in/1138 out, quality mean 0.88).
- SLO đã chọn và lý do: P95 latency ≤ 3000 ms (99.5%), error rate ≤ 2% (99.0%), daily cost ≤ $2.50 (100.0%) và quality proxy ≥ 0.75 (95.0%). Các ngưỡng này khớp `config/dashboard.yaml`; baseline dashboard hiện tại (P95 151 ms, 0.00% lỗi, $0.0181 cost, quality 0.88) đang đạt, đồng thời ngưỡng vẫn đủ rõ để phát hiện incident `rag_slow`, `tool_fail` hoặc `cost_spike`.
- Alert rules và runbook: Hoàn thiện 3 alert symptom-based trong `config/alert_rules.yaml` và runbook Metrics → Traces → Logs trong `docs/alerts.md`: `high_latency_p95`, `elevated_error_rate`, `cost_budget_exceeded`.

## 6. Điều tra challenge

- Challenge ID: `day13-k3-observability-v1` (incident: `rag_slow`, feature ảnh hưởng: `refund`, seed: 1303, ngưỡng latency 2000ms)
- Triệu chứng từ metrics: Trong cửa sổ incident, `latency_p95` tăng vọt lên **3740ms** so với baseline ~1–1.9s (SLO objective 3000ms bị vượt). `error_rate_pct` giữ ở 0%, cost/tokens bình thường → chỉ có latency bất thường, không phải `tool_fail` hay `cost_spike`. Xem `submission/evidence/cp3-metrics.json`.
- Trace ID liên quan: Xem danh sách trace `feature=refund` trong cửa sổ 04:31 UTC trên Langfuse; nối theo `correlation_id` trong metadata trace. (Chụp ảnh waterfall `run` lồng `retrieve`/`generate` — span `retrieve` chiếm phần lớn thời gian, xem `submission/evidence/cp3-trace-waterfall.png`.)
- Log line/correlation ID liên quan: `req-4930678c` — `request_received` lúc `04:31:17.089Z`, `response_sent` lúc `04:31:20.831Z`, `latency_ms: 3740`. Cả 5 request `refund` đều có `latency_ms` 3.5–3.7s dù `tokens_in/out` nhỏ. Xem toàn bộ tại `submission/evidence/cp3-logs.jsonl`.
- Root cause: `rag_slow` làm hàm `retrieve()` trong `app/mock_rag.py` chèn `time.sleep(2.5)` trước khi trả tài liệu, kéo tổng latency mỗi request vượt ngưỡng. Nhờ trace sub-component (`@observe(as_type="span")` trên `retrieve`), span RAG chiếm gần như toàn bộ thời gian, trong khi span LLM (`generate`) giữ ~0.15s bình thường → root cause nằm ở tầng retrieval, không phải LLM.
- Fix action: (1) Thêm timeout/circuit-breaker cho RAG retrieval; (2) giảm độ trễ lookup (cache kết quả truy vấn trùng, index song song); (3) nếu retrieval không đáp ứng deadline, trả fallback context thay vì chặn request.
- Preventive measure: (1) Thêm alert symptom-based `high_latency_p95` (có sẵn trong `docs/alerts.md#alert-1`) để phát hiện sớm; (2) đặt SLO P95 ≤ 3000ms và giám sát trend; (3) chạy load test định kỳ với baseline latency; (4) giữ trace sub-component để khoanh vùng nhanh RAG vs LLM trong mỗi incident.

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.


| Thành viên                        | Phần việc                                                                                                                                                                                                                                                                                                                                                           | Commit/PR                                                           | Điều đã học                                                                                                                                                                                                                  |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Đồng Đại Huy (2A202601901)      | CP1 Middleware; tạo, kiểm tra và truyền Correlation ID; bổ sung exception handler an toàn; viết test cho middleware và lỗi request                                                                                                                                                                                                                           | Chưa commit/PR riêng                                              | Cách dùng middleware và contextvars để gắn correlation ID xuyên suốt request, xử lý lỗi an toàn và kiểm chứng bằng test                                                                                           |
| Phạm Đức Trung (2A202601253)     | CP1 PII Scrubbing: thêm pattern passport/địa chỉ Việt Nam; bật scrubber trước khi ghi JSON; scrub dữ liệu lồng nhau và bổ sung test PII/logging                                                                                                                                                                                                          | `add4bfb` — feat: xong viec thanh vien B                           | Che PII tại logging boundary, giữ schema log ổn định và kiểm chứng dữ liệu nhạy cảm không lọt qua các field lồng nhau                                                                                             |
| Nguyễn Quang Tường (2A202601597) | CP1/CP2 Metrics & Dashboard: đo`error_rate_pct` từ `data/logs.jsonl`, viết `scripts/build_dashboard.py` tự tính đủ 6 nhóm chỉ số (latency, traffic, errors, cost, tokens, quality) theo contract `config/dashboard.yaml`, chạy `validate_dashboard.py` và thu thập evidence (`submission/evidence/screendashboard.png`, `validate_dashboard_output.txt`) | Chưa commit/PR riêng                                              | Cách định nghĩa và tính`error_rate_pct`/percentile latency thống nhất giữa nhiều nguồn (log thô, `/metrics`, dashboard), và cách ràng buộc một dashboard tự dựng vào đúng contract YAML để pass validator |
| Phạm Đình Minh (2A202601979)    | CP2 SRE & Alerts: đặt SLO cho latency, error, cost, quality; viết 3 alert rules symptom-based và runbook điều tra/mitigation theo Metrics → Traces → Logs; bổ sung`error_rate_pct` cho endpoint metrics                                                                                                                                                      | `77dee42` — feat: complete SRE alerts and expose error rate metric | Cách đặt SLO từ dashboard contract, thiết kế alert theo ảnh hưởng người dùng và biến alert thành quy trình điều tra có evidence                                                                                |
| Nguyễn Đình Bình (2A202601091)  | Chạy load test (baseline + challenge); bọc trace sub-component RAG/LLM bằng`@observe(as_type="span")` trong `app/mock_rag.py` và `app/mock_llm.py` (phần mở rộng); dẫn dắt điều tra Challenge CP3: nối Metrics → Traces → Logs, chứng minh root cause `rag_slow` với correlation ID `req-4930678c`; hoàn thiện REPORT mục 3/6 và evidence CP3     | Commit sẽ đánh dấu sau (bọc span + REPORT)                     | Waterfall sub-component giúp khoanh vùng RAG vs LLM; quy trình điều tra dựa trên bằng chứng 3 lớp thay vì đoán                                                                                                       |
