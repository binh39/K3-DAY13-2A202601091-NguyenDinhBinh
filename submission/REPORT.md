# Báo cáo Day 13 Observability

## 1. Thông tin nhóm

- Tên nhóm:
- Repository URL:
- Commit SHA cuối:
- Thành viên và vai trò:
  - Đồng Đại Huy (2A202601901) — API & Middleware: triển khai CP1 Middleware, gán Correlation ID và bổ sung exception handler mở rộng.
  - Phạm Đức Trung (2A202601253) — Security Engineer: triển khai PII scrubbing, mở rộng regex PII và kiểm chứng log không lộ dữ liệu nhạy cảm.

## 2. Kết quả kỹ thuật

- Điểm `validate_logs.py`: 30/100 (baseline CP0, trước khi hoàn thiện correlation ID và log enrichment)
- Tổng số traces:
- Số PII leak còn lại:
- Link/đường dẫn dashboard:

## 3. Logging và tracing

- Evidence correlation ID:
- Evidence PII redaction:
- Evidence trace waterfall:
- Giải thích một span đáng chú ý:

## 4. Prompt versioning

- Prompt name:
- Version/label baseline:
- Version/label candidate:
- Trace ID của mỗi version:
- Bằng chứng đổi label hoặc rollback:

## 5. Dashboard, SLO và alerts

- Kết quả `validate_dashboard.py`: HỢP LỆ: 6/6 panel có trong dashboard contract. (xem `submission/evidence/validate_dashboard_output.txt`)
- Evidence dashboard: `submission/evidence/scrdashboard.png` (đủ 6 panel: latency, traffic, errors, cost, tokens, quality — tên panel + time range hiển thị rõ, cả 6 panel đều OK: latency P95=151ms, traffic 10 req/phút, error_rate_pct=0.00% (0/10), cost $0.0181, tokens 330 in/1138 out, quality mean 0.88).
- SLO đã chọn và lý do: [D điền]
- Alert rules và runbook: [D điền]

## 6. Điều tra challenge

- Challenge ID:
- Triệu chứng từ metrics:
- Trace ID liên quan:
- Log line/correlation ID liên quan:
- Root cause:
- Fix action:
- Preventive measure:

## 7. Đóng góp cá nhân

Với mỗi thành viên, ghi rõ nhiệm vụ và link commit/PR tương ứng.

| Thành viên | Phần việc | Commit/PR | Điều đã học |
|---|---|---|---|
| Đồng Đại Huy (2A202601901) | CP1 Middleware; tạo, kiểm tra và truyền Correlation ID; bổ sung exception handler an toàn; viết test cho middleware và lỗi request | Chưa commit/PR riêng | Cách dùng middleware và contextvars để gắn correlation ID xuyên suốt request, xử lý lỗi an toàn và kiểm chứng bằng test |
| Phạm Đức Trung (2A202601253) | CP1 PII Scrubbing: thêm pattern passport/địa chỉ Việt Nam; bật scrubber trước khi ghi JSON; scrub dữ liệu lồng nhau và bổ sung test PII/logging | `add4bfb` — feat: xong viec thanh vien B | Che PII tại logging boundary, giữ schema log ổn định và kiểm chứng dữ liệu nhạy cảm không lọt qua các field lồng nhau |
| Nguyễn Quang Tường (2A202601597) | CP1/CP2 Metrics & Dashboard: đo `error_rate_pct` từ `data/logs.jsonl`, viết `scripts/build_dashboard.py` tự tính đủ 6 nhóm chỉ số (latency, traffic, errors, cost, tokens, quality) theo contract `config/dashboard.yaml`, chạy `validate_dashboard.py` và thu thập evidence (`submission/evidence/screendashboard.png`, `validate_dashboard_output.txt`) | Chưa commit/PR riêng | Cách định nghĩa và tính `error_rate_pct`/percentile latency thống nhất giữa nhiều nguồn (log thô, `/metrics`, dashboard), và cách ràng buộc một dashboard tự dựng vào đúng contract YAML để pass validator |
