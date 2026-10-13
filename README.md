# Price Tracker Bot

## Telegram: tiếp nhận yêu cầu

Yêu cầu Python 3.11 trở lên. Trong thư mục gốc dự án:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Tạo bot qua https://t.me/BotFather bằng `/newbot`. Thêm token vào `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=your_token_here
```

Không commit hoặc chia sẻ token. `.env` đã được bỏ qua trong Git.

```powershell
.\.venv\Scripts\python.exe main.py
```

Mở chat riêng với bot và gửi `/start`, `/help`, `/add <url>` hoặc một URL thuần.
Mỗi tin chỉ nhận một URL, hiện hỗ trợ HTTPS của books.toscrape.com.
Bot phản hồi hướng dẫn nếu nhập sai, gửi ảnh hoặc lệnh không hỗ trợ.
Bot chỉ nhận chat riêng, không xử lý nhóm ở bước này.

Yêu cầu gần nhất của mỗi người được giữ trong RAM: user_id, chat_id,
message_id, url, received_at. Gửi yêu cầu mới thay thế yêu cầu cũ; dừng bot
sẽ mất dữ liệu. URL được tải để lấy thông tin sách; chưa lưu theo dõi lâu dài.
Ngưỡng giá và lưu trữ sẽ bổ sung trong bước tiếp theo.

Chạy kiểm thử không cần token hoặc kết nối Telegram:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_telegram_bot.py" -v
```

## Tra giá ngay qua Telegram

Gửi link chi tiết một cuốn sách hoặc `/add <url>`. Bot báo đang xử lý,
rồi trả tên, giá GBP, tình trạng hàng, thời điểm kiểm tra UTC và URL.
Lỗi mạng, timeout hoặc trang không có chi tiết sách sẽ có phản hồi tương ứng.
Chức năng này gọi `src/scraper/scrape_demo.py`, chưa lưu lịch sử hoặc theo dõi định kỳ.
Khởi động lại bot sau khi cập nhật code bằng `python main.py`.

## Tra tỷ giá

Thêm `ALLRATESTODAY_API_KEY` vào `.env` và khởi động lại bot.
Gửi `/rate USD VND`, `/rate EUR VND` hoặc `/rate JPY USD`.
Chỉ trả tỷ giá của 1 đơn vị tiền nguồn, không nhận số tiền quy đổi.
Dữ liệu mid-market kèm thời điểm do nguồn cung cấp, không phải giá mua/bán ngân hàng.
Mỗi lệnh hợp lệ gọi API một lần; không retry khi hết quota.
Tài liệu: https://allratestoday.com/docs/

## Cấu hình và models

`src/settings.py` đọc `.env` từ gốc repository, không phụ thuộc thư mục terminal.
Biến môi trường của hệ điều hành được ưu tiên hơn `.env`. Khởi động lại sau khi đổi cấu hình.
Các giá trị mặc định và tên biến nằm trong `.env.example`.
Timeout tính bằng giây. SCRAPER_MAX_REQUESTS là số lượt tải trong chuỗi chuyển hướng,
không phải số lần retry. BOT_BOOTSTRAP_RETRIES chỉ áp dụng khi khởi động Telegram.
Không bật HTTPX_LOG_LEVEL=INFO/DEBUG khi vận hành vì log request có thể chứa token.
Giữ ALLRATESTODAY_BASE_URL là nguồn đáng tin cậy vì API key được gửi tới địa chỉ này.

Dataclass được đặt tại `src/models/book_detail.py`, `exchange_rate.py`, `product_request.py`.
Quy tắc giao thức (HTTP status, tên header), selector HTML, GBP và regex giá của
Books to Scrape được giữ trong code vì chúng thuộc hợp đồng dữ liệu, không phải cấu hình vận hành.
Chạy scraper bằng `python -m src.scraper.scrape_demo` từ gốc dự án.

Thông báo lỗi AllRatesToday được cấu hình bằng các biến `RATE_ERROR_*` trong `.env`.
Giữ dấu nháy quanh nội dung; khởi động lại bot sau khi sửa. Biến trống dùng thông báo mặc định.
`RateError` đặt trong `src/exceptions/rate_error.py`; các dataclass dữ liệu vẫn ở `src/models`.

Nội dung phản hồi Telegram dùng các biến `BOT_MSG_*` trong `.env`.
Dùng dấu nháy kép và `\n` để xuống dòng. Giữ nguyên tên `{placeholder}` như mẫu trong `.env.example`.
Các giá trị price/rate được định dạng sẵn trong code; không thêm format spec vào placeholder.
Khởi động lại bot sau khi đổi nội dung. Placeholder không hợp lệ sẽ báo lỗi lúc khởi động.

Các ValueError của scraper dùng biến `SCRAPER_ERROR_*` trong `.env`.
Giữ `{price_text}` trong mẫu lỗi giá; code tự chèn biểu diễn chuỗi đầu vào. Khởi động lại để áp dụng.

`DISPLAY_TIMEZONE=Asia/Ho_Chi_Minh` hiển thị giờ Việt Nam (UTC+07:00) trong kết quả tỷ giá.
Có thể đổi sang tên IANA khác như `UTC` hoặc `Asia/Bangkok`, rồi khởi động lại bot.
Thời điểm gốc từ API được giữ nguyên; chỉ chuyển múi giờ lúc hiển thị.
