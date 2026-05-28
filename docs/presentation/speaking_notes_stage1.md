# Speaking Notes — Stage 1: Enrichment & Dual-Vector Indexing

**Slide:** Stage 1 — Enrichment & Dual-Vector Indexing
**Estimated speaking time:** ~90 giây (60s narration + 30s buffer)
**Created:** 2026-05-16

---

## Mục lục

1. Opening hook
2. Walkthrough — Enrichment zone
3. Walkthrough — Indexing zone
4. Key insight: shared embedding space
5. Anticipated Q&A
6. Bridge sang slide kế tiếp
7. Personal notes (để bạn fill thêm)

---

## 1. Opening hook (10–15s)

**Vietnamese (chính thức dùng):**

> "Stage 1 là bước **offline** — chuẩn bị dữ liệu trước khi user truy vấn. Pipeline gồm hai zones — bên trái là **ENRICHMENT** dùng Gemini để bóc thêm thông tin từ ảnh; bên phải là **INDEXING** encode dữ liệu thành vectors để truy vấn nhanh ở runtime."

**English alternative (nếu reviewer hỏi tiếng Anh):**

> "Stage 1 is the offline pipeline that prepares data before any user query. Two zones — Enrichment on the left uses Gemini to extract additional information from images; Indexing on the right encodes everything into vectors for fast retrieval at runtime."

**Gesture:** Chỉ tay vào title, sau đó vào 2 zones từ trái sang phải.

---

## 2. Walkthrough — Enrichment zone (25–30s)

> "Dữ liệu đầu vào là từng item — một ảnh quần áo cộng với label thô từ Kaggle dataset, ví dụ 't-shirt'. Vấn đề: label đó **quá generic** — không đủ để match với truy vấn như 'áo cotton tay ngắn cho ngày hè'.
>
> Em dùng Gemini **hai lần riêng biệt**, không gộp một call. Mỗi call có vai trò khác nhau:
>
> **Call 1 — Caption.** Gemini sinh ra một caption mô tả fashion-specific, ví dụ *'a light blue cotton crewneck t-shirt with a relaxed fit'*. Quy tắc: **cấm dùng category words generic** như 'shirt', 'item' — để tránh model học bias về category thay vì attribute.
>
> **Call 2 — Color.** Gemini chỉ trả về dominant color tag, ví dụ *'blue'*. Đây là structured output, ngắn gọn, dùng cho cả filter và BM25 token."

**Gesture:** Chỉ vào hai box trong amber zone khi nói tên call. Khi đọc ví dụ caption, có thể giơ 1 ngón trỏ để emphasize "cấm generic".

**Nhấn mạnh:** "Hai call **tách biệt** — đây là decision có chủ đích, không phải technical limitation."

---

## 3. Walkthrough — Indexing zone (25–30s)

> "Sau enrichment, dữ liệu chảy xuống **Postgres** làm source of truth — đây là chỗ chúng ta có thể replay pipeline mà không cần gọi lại Gemini.
>
> Từ Postgres, indexing zone đọc lên theo hai nhánh:
>
> **SigLIP Encoder** — Marqo-FashionSigLIP, model fine-tune trên domain thời trang, 768 chiều. Mỗi item sinh ra **hai vectors**: image vector từ ảnh, text vector từ chuỗi *'label + color + caption'*. Cả hai vectors **cùng nằm trong embedding space** — em sẽ quay lại điểm này.
>
> **BM25 Composer** — sparse keyword index. Em chỉ lấy *'label + color'* — captions cố tình **không vào BM25** vì sẽ làm noisy keyword search. Captions để dành cho **cross-encoder rerank** ở stage 2.
>
> Tất cả ba outputs — image vector, text vector, BM25 tokens — ghi vào **Qdrant** như một point per item."

**Gesture:** Chỉ vào SigLIP box, đọc "768-d image vector" rồi "768-d text vector" rõ ràng. Khi nói "cùng embedding space", dùng tay khoanh vòng tròn ôm cả 2 vector.

---

## 4. Key insight — Shared embedding space (10–15s)

> "Điểm kiến trúc quan trọng nhất của stage 1: **image vector và text vector cùng nằm trong embedding space của SigLIP**.
>
> Điều này có nghĩa: ở runtime, truy vấn text 'áo cotton màu xanh' có thể **match trực tiếp** với image vector của các ảnh áo cotton xanh — không cần convert qua intermediate representation. Đây là nền tảng cho **cross-modal hybrid retrieval** mà em sẽ trình bày trong stage tiếp theo."

**Gesture:** Dừng lại 1-2 giây để reviewer ngấm. Đây là **takeaway chính** của slide.

---

## 5. Anticipated Q&A

### Q1: "Vì sao tách caption và color thành hai Gemini call riêng?"

> Hai trục thông tin khác nhau. Caption là prose descriptive — dùng cho text-vector. Color là structured tag — dùng cho filter và BM25 token. Em đã thử gộp một call: output không stable, đôi lúc caption chứa color, đôi lúc color bị nhúng vào caption. Tách riêng cho schema chắc chắn và parser đơn giản. Trade-off: tốn thêm một LLM call per item ở stage offline, nhưng offline cost không phải bottleneck.

### Q2: "Sao không dùng CLIP thay SigLIP?"

> Marqo-FashionSigLIP được fine-tune trên fashion domain — embedding space đã shifted về thuật ngữ thời trang. CLIP general-purpose hơn nhưng cho fashion-specific search thì recall kém hơn. Trong literature, SigLIP cũng được report cho better contrastive performance so với CLIP ở cùng số chiều.

### Q3: "Captions không vào BM25 — vì sao?"

> Captions dài và chứa nhiều stopwords cùng descriptors không có giá trị cho keyword search. BM25 cần anchor terms — label và color đã đủ vai trò đó. Em không muốn BM25 score bị dilute bởi từ như "relaxed", "crewneck" — những từ đó để cross-encoder hiểu semantic ở rerank stage.

### Q4: "Pipeline này có chạy lại không? Cost Gemini bao nhiêu?"

> Idempotent — chạy lại chỉ cho items mới trong Postgres mà chưa có vector trong Qdrant. Em có backup Postgres và Qdrant, restore không cần re-enrich. Cost Gemini cho dataset pilot khoảng vài đô-la one-time, không scale theo session.

### Q5: "Vector 768 chiều — có quá nhỏ không?"

> 768 là dimension chuẩn của SigLIP base. Tăng dimension không nhất thiết tăng quality — fashion attribute space không quá rộng. Trade-off: 768 đủ chính xác cho domain này, đồng thời ANN search trong Qdrant nhanh hơn so với 1024 hoặc 1536. Em đã đo recall — không thấy gain rõ rệt khi thử với higher dim.

### Q6: "Sao Postgres lại nằm giữa enrichment và indexing?"

> Postgres là **source of truth**. Có ba lý do:
>
> 1. **Audit**: Em có thể xem caption Gemini sinh ra cho bất kỳ item nào.
> 2. **Replay**: Nếu thay SigLIP bằng model khác, em re-encode từ Postgres mà không gọi lại Gemini.
> 3. **Schema flexibility**: Qdrant không phải nơi lưu metadata phong phú — Postgres handle structured queries.

### Q7: "Stage 1 chạy mất bao lâu?"

> Cho dataset pilot ~5,000 items, end-to-end khoảng 2-3 giờ. Bottleneck là Gemini API rate limit, không phải compute local. SigLIP encoding chạy GPU ~10 phút cho toàn dataset.

---

## 6. Bridge sang slide kế tiếp

**Nếu slide kế là Stage 2 (Hybrid Retrieval):**

> "Với dữ liệu đã indexed sẵn — image vectors, text vectors, BM25 tokens — câu hỏi tiếp theo là: **làm sao kết hợp ba phương pháp này** để retrieval tốt hơn từng phương pháp riêng? Đó là nội dung Stage 2."

**Nếu slide kế là Architecture Pipeline:**

> "Stage 1 chỉ là phần offline. Khi user gửi query, hệ thống cần điều phối Agent và Hybrid RAG cùng làm việc — và đó là kiến trúc trong slide tiếp theo."

---

## 7. Personal notes (bạn fill thêm)

> *Để trống — bạn có thể ghi:*
>
> - Câu nói riêng muốn dùng
> - Số liệu cụ thể cần check trước buổi defend
> - Reviewer nào dễ hỏi câu nào
> - Backup arguments nếu bị challenged
> - Demo flow nếu cần show live

---

## 8. Checklist trước khi lên slide này

- Đã pre-cache SigLIP và BGE models trên máy demo
- Đã verify Postgres + Qdrant container đang running
- Đã có ví dụ ảnh + caption thật để show nếu reviewer hỏi
- Đã rehearse câu "shared embedding space" sao cho rõ ràng
- Đã prepare answer cho Q1, Q2, Q6 (most likely hỏi)

---

*File này em soạn để defend Stage 1. Có thể edit thêm vào section 7 hoặc bất kỳ chỗ nào — anh sẽ giúp polish.*
