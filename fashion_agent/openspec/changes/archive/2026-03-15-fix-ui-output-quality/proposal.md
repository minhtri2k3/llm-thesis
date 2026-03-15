## Why

Giao diện Gradio hiện tại hiển thị kết quả tìm kiếm sản phẩm rất xấu và thiếu chuyên nghiệp:

1. **Sản phẩm "rác" bị hiển thị:** Một số sản phẩm trả về từ search engine bị thiếu caption, color, hoặc không có ảnh → UI vẫn in ra dạng `"2. T-Shirt —"` trống trơn, gây confusion cho người dùng.
2. **Ảnh và text tách rời:** Phần text mô tả sản phẩm được in trước, ảnh sản phẩm lại nhét sau cùng thành một khối riêng biệt → người dùng không biết ảnh nào ứng với sản phẩm nào.
3. **Luôn cố output 6 sản phẩm:** Dù chỉ tìm thấy 2 sản phẩm hợp lệ, hệ thống vẫn "cố gắng" đưa ra đủ 6 kết quả bao gồm cả kết quả rác.

Cần fix ngay để demo UI đủ chất lượng trình bày trong luận văn.

## What Changes

- **Lọc sản phẩm rác ở tầng UI:** Chỉ hiển thị sản phẩm có đầy đủ `image_path` (file tồn tại), `label` không rỗng. Nếu chỉ 2/6 sản phẩm hợp lệ → chỉ output 2.
- **Hiển thị ảnh inline:** Mỗi sản phẩm hiển thị ảnh ngay bên dưới phần mô tả text (dạng card), thay vì tách ảnh ra thành khối riêng.
- **Tăng limit caption hiển thị:** Nâng từ 100 ký tự lên 150 ký tự để mô tả sản phẩm rõ hơn.
- **Cải thiện format Markdown:** Bỏ dấu `—` khi color rỗng, thêm khoảng cách hợp lý giữa các sản phẩm.

## Capabilities

### New Capabilities
- `product-display-filter`: Lọc và chỉ hiển thị sản phẩm có thông tin đầy đủ (image_path hợp lệ, label không rỗng) tại tầng UI, không output sản phẩm rác.
- `inline-product-cards`: Hiển thị ảnh sản phẩm inline (dạng thẻ) ngay sau phần mô tả text của từng sản phẩm, thay vì gom ảnh thành khối riêng biệt ở cuối.

### Modified Capabilities
_(Không có capability hiện tại nào bị thay đổi ở mức spec)_

## Impact

- **File chính:** `api/main.py` — hàm `respond()` trong Gradio UI
- **Logic bị ảnh hưởng:** Cách render kết quả sản phẩm trong chatbot Gradio
- **Không ảnh hưởng:** Search engine, agent logic, database, indexing pipeline
- **Không breaking change:** API endpoint `/api/chat` trả về dữ liệu giống cũ, chỉ UI render khác
