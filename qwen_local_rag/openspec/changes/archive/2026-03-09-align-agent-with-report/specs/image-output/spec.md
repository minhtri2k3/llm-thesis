## ADDED Requirements

### Requirement: Docker volume mount cho dataset images
Docker container fashion-api SHALL mount thư mục ảnh dataset từ host vào container tại `/app/dataset_images` ở chế độ read-only. Path host MUST được cấu hình qua environment variable `DATASET_IMAGES_HOST_PATH`.

#### Scenario: Container khởi động với ảnh accessible
- **WHEN** `docker compose up -d fashion-api` được chạy với `DATASET_IMAGES_HOST_PATH` set
- **THEN** container CÓ THỂ đọc file ảnh .jpg tại `/app/dataset_images/`

#### Scenario: Fallback khi không mount
- **WHEN** `DATASET_IMAGES_HOST_PATH` không được set
- **THEN** system vẫn hoạt động, chỉ không hiển thị ảnh (graceful degradation)

### Requirement: Convert image_path sang container path
Hàm respond() trong api/main.py SHALL convert image_path từ host absolute path sang container path bằng cách extract basename.

#### Scenario: Convert path thành công
- **WHEN** search trả về `image_path = "/Users/letri/.cache/.../ea7b6656.jpg"`
- **THEN** system convert thành `/app/dataset_images/ea7b6656.jpg`

#### Scenario: File không tồn tại
- **WHEN** converted path không tồn tại trong container
- **THEN** system bỏ qua ảnh đó, vẫn hiển thị text response

### Requirement: Gradio Chatbot hiển thị ảnh sản phẩm
respond() SHALL trả về ảnh sản phẩm trong Gradio Chatbot messages format. Mỗi ảnh MUST có alt_text chứa label và color.

#### Scenario: Search trả về sản phẩm có ảnh
- **WHEN** agent tìm được 6 sản phẩm với image_path hợp lệ
- **THEN** Gradio hiển thị text answer trước, sau đó hiển thị từng ảnh với caption

#### Scenario: Search trả về 0 sản phẩm
- **WHEN** không tìm thấy sản phẩm nào
- **THEN** chỉ hiển thị text response, không có ảnh
