## ADDED Requirements

### Requirement: Hiển thị ảnh sản phẩm inline ngay sau mô tả text
Hệ thống SHALL hiển thị ảnh sản phẩm trực tiếp trong cùng một message chatbot, nằm ngay bên dưới phần text mô tả (label, color, caption) của sản phẩm đó. MUST KHÔNG tách ảnh thành message riêng biệt.

#### Scenario: Sản phẩm có đầy đủ thông tin
- **WHEN** sản phẩm hợp lệ có label, color, caption, và image_path
- **THEN** UI MUST render 1 block gồm: tiêu đề (`label — color`), mô tả (`caption` tối đa 150 ký tự), và ảnh ngay bên dưới trong cùng 1 message

#### Scenario: Nhiều sản phẩm hiển thị tuần tự
- **WHEN** có N sản phẩm hợp lệ (N > 1)
- **THEN** UI MUST render N product cards liên tiếp trong 1 message, mỗi card gồm text + ảnh inline, có khoảng cách rõ ràng giữa các cards

#### Scenario: Ảnh được constrain kích thước
- **WHEN** UI render ảnh sản phẩm inline
- **THEN** ảnh MUST có width tối đa 220px với border-radius bo góc để trông gọn gàng

### Requirement: Không còn multi-message cho ảnh sản phẩm
Hệ thống MUST KHÔNG gửi ảnh sản phẩm dưới dạng message riêng biệt (tách khỏi text mô tả). Tất cả output (text + ảnh) MUST nằm trong 1 assistant message duy nhất.

#### Scenario: Output chỉ có 1 assistant message
- **WHEN** agent trả về kết quả tìm kiếm với N sản phẩm
- **THEN** UI MUST render đúng 1 assistant message chứa cả text mô tả + ảnh inline, không có message ảnh riêng biệt phía sau
