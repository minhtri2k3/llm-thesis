## MODIFIED Requirements

### Requirement: Endpoint serve ảnh phải tìm đúng thư mục dataset

#### Scenario: Ảnh tồn tại trong dataset
- **WHEN** client request `GET /api/images/{uuid}.jpg`
- **AND** file tồn tại tại `DATASET_IMAGES_DIR/{uuid}.jpg`
- **THEN** endpoint MUST trả về ảnh với status 200

#### Scenario: Ảnh không tồn tại
- **WHEN** file không tồn tại ở cả `DATASET_IMAGES_DIR` lẫn `IMAGES_DIR`
- **THEN** endpoint MUST trả về 404
