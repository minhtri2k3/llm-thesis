## ADDED Requirements

### Requirement: Lọc sản phẩm không hợp lệ trước khi hiển thị
Hệ thống SHALL lọc bỏ các sản phẩm không đủ thông tin tối thiểu trước khi render UI. Sản phẩm MUST có `image_path` trỏ tới file ảnh tồn tại trong hệ thống VÀ `label` không rỗng để được hiển thị.

#### Scenario: Sản phẩm thiếu image_path
- **WHEN** search engine trả về sản phẩm có `image_path` rỗng hoặc `None`
- **THEN** sản phẩm đó MUST bị loại bỏ khỏi danh sách hiển thị

#### Scenario: Sản phẩm có image_path nhưng file không tồn tại
- **WHEN** search engine trả về sản phẩm có `image_path` nhưng file ảnh không tồn tại trên filesystem
- **THEN** sản phẩm đó MUST bị loại bỏ khỏi danh sách hiển thị

#### Scenario: Sản phẩm thiếu label
- **WHEN** search engine trả về sản phẩm có `label` rỗng hoặc `None`
- **THEN** sản phẩm đó MUST bị loại bỏ khỏi danh sách hiển thị

#### Scenario: Chỉ output sản phẩm hợp lệ
- **WHEN** search engine trả về 6 kết quả nhưng chỉ 2 sản phẩm thỏa điều kiện hợp lệ
- **THEN** UI MUST chỉ hiển thị 2 sản phẩm đó, không pad thêm kết quả rác

#### Scenario: Sản phẩm thiếu caption hoặc color vẫn hiển thị
- **WHEN** sản phẩm có đủ `image_path` hợp lệ và `label` không rỗng nhưng thiếu `caption` hoặc `color`
- **THEN** sản phẩm vẫn MUST được hiển thị, bỏ qua phần thông tin thiếu

#### Scenario: Color rỗng không hiển thị dấu gạch ngang
- **WHEN** sản phẩm hợp lệ nhưng `color` rỗng
- **THEN** tiêu đề sản phẩm MUST hiển thị chỉ `label` mà không có ` — ` thừa
