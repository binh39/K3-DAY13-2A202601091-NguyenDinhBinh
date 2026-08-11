# Alert runbook

Các alert dưới đây dựa trên triệu chứng người dùng hoặc SLO. Khi điều tra, luôn theo luồng Metrics → Traces → Logs và chỉ kết luận root cause khi evidence ở ba lớp khớp nhau.

## Alert 1

- Tên: `high_latency_p95`.
- Severity: `warning`.
- SLI/SLO liên quan: `latency_p95_ms`; P95 không vượt 3000 ms trong 99.5% request của cửa sổ 28 ngày.
- Điều kiện và thời gian duy trì: `latency_p95 > 3000ms` trong 5 phút liên tục.
- Ảnh hưởng tới người dùng: người dùng thấy phản hồi chat chậm hoặc hết thời gian chờ.
- Ba bước kiểm tra đầu tiên:
  1. Mở panel Latency trong dashboard, xác nhận P95 vượt 3000 ms và xác định khoảng thời gian ảnh hưởng.
  2. Mở Langfuse, lọc trace trong khoảng thời gian đó, so sánh thời lượng `run` và các span `retrieve`/`generate` nếu đã bật sub-spans.
  3. Lấy `correlation_id` từ trace, tìm các log cùng ID để xác nhận lỗi, dependency chậm hoặc feature bị ảnh hưởng.
- Mitigation tạm thời: chuyển sang câu trả lời fallback khi retrieval chậm, giảm concurrency hoặc rollback thay đổi gây tăng latency; chỉ tắt incident practice bằng script khi đang demo lab.
- Owner: `on-call-engineer`.

## Alert 2

- Tên: `elevated_error_rate`.
- Severity: `critical`.
- SLI/SLO liên quan: `error_rate_pct`; tỷ lệ lỗi không vượt 2% trong 99.0% cửa sổ 28 ngày.
- Điều kiện và thời gian duy trì: `error_rate_pct > 5` trong 3 phút liên tục. Ngưỡng critical này cao hơn SLO 2% để tránh báo động liên tục cho một dao động ngắn; SLO breach vẫn phải được theo dõi trên dashboard.
- Ảnh hưởng tới người dùng: một phần request không nhận được câu trả lời và nhận HTTP 500 hoặc thông báo lỗi.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận Error panel tăng và xem `error_breakdown` để biết loại lỗi chiếm đa số.
  2. Mở một trace lỗi gần nhất để xác định feature, session và span có trạng thái lỗi.
  3. Dùng `correlation_id` lọc `data/logs.jsonl`, đối chiếu `request_received` với `request_failed` và chi tiết exception đã được redact.
- Mitigation tạm thời: bật fallback an toàn, cô lập dependency lỗi hoặc rollback bản phát hành gần nhất; không xóa log lỗi hay tạo evidence giả.
- Owner: `on-call-engineer`.

## Alert 3

- Tên: `cost_budget_exceeded`.
- Severity: `warning`.
- SLI/SLO liên quan: `daily_cost_usd`; tổng chi phí LLM mỗi ngày không vượt 2.50 USD.
- Điều kiện và thời gian duy trì: `daily_cost_usd > 2.5` trong ngày hiện tại.
- Ảnh hưởng tới người dùng: chưa nhất thiết có lỗi ngay, nhưng ngân sách có thể cạn và dịch vụ có nguy cơ bị giới hạn sau đó.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận tổng cost trong Cost panel và đối chiếu với tổng theo ngày từ các event `response_sent`.
  2. Mở các trace có `cost_details.total` hoặc output token cao, so sánh model, feature và prompt version.
  3. Dùng `correlation_id` tra log để xác nhận request tạo token/cost bất thường, đồng thời kiểm tra `cost_spike` hay thay đổi prompt gần đây.
- Mitigation tạm thời: giới hạn output tokens, dùng prompt ngắn hơn, cache response lặp lại hoặc chuyển workload phù hợp sang model rẻ hơn; đánh giá lại chi phí sau thay đổi.
- Owner: `team-lead`.
