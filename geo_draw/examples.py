"""Sample problems offered on the empty chat screen (web, Streamlit and mobile)."""

EXAMPLES = {
    "Tam giác vuông": "Cho tam giác ABC vuông tại A, AB = 3, AC = 4.",
    "Tam giác + nhiều yêu cầu": (
        "Cho tam giác ABC vuông tại A, AB = 4, AC = 6. Gọi M là trung điểm BC. "
        "Kẻ đường cao AH. Qua M kẻ đường thẳng song song với AB, cắt AC tại N. "
        "Vẽ đường tròn tâm M đi qua B."
    ),
    "Đường tròn + tiếp tuyến": (
        "Cho đường tròn tâm O bán kính 3 và điểm A nằm ngoài đường tròn. "
        "Từ A kẻ hai tiếp tuyến AB, AC với đường tròn, B và C là các tiếp điểm. Vẽ OA, OB, OC."
    ),
    "Hình vuông": "Cho hình vuông ABCD cạnh 4. Vẽ hai đường chéo AC và BD, đánh dấu giao điểm O.",
    "Các đường đặc biệt và góc": (
        "Cho tam giác ABC có AB = 5, AC = 6 và góc BAC = 60°. Gọi M là trung điểm BC; "
        "vẽ trung tuyến AM. Kẻ đường cao AH, phân giác AD và đường trung trực của BC. "
        "Đánh dấu các góc bằng nhau và các góc vuông."
    ),
}

# Offered by the web app, which solves any math problem and draws geometry figures.
MATH_EXAMPLES = [
    {"topic": "Phương trình", "name": "Phương trình bậc hai",
     "problem": "Giải phương trình $x^2 - 5x + 6 = 0$."},
    {"topic": "Hệ phương trình", "name": "Bài toán thực tế",
     "problem": ("Một mảnh vườn hình chữ nhật có chu vi 34 m. Nếu tăng chiều dài thêm 3 m và "
                 "tăng chiều rộng thêm 2 m thì diện tích tăng thêm 45 m². Tính chiều dài và "
                 "chiều rộng của mảnh vườn.")},
    {"topic": "Hàm số", "name": "Hàm số bậc nhất",
     "problem": ("Cho hàm số $y = (m - 1)x + 2m - 3$. Tìm $m$ để đồ thị hàm số song song với "
                 "đường thẳng $y = 3x + 1$.")},
    {"topic": "Hình học", "name": "Tam giác vuông, đường cao",
     "problem": ("Cho tam giác ABC vuông tại A, AB = 6 cm, AC = 8 cm, đường cao AH. "
                 "a) Tính BC và AH. b) Gọi M là trung điểm BC. Chứng minh AM = BC/2.")},
    {"topic": "Hình học", "name": "Đường tròn, tiếp tuyến",
     "problem": ("Cho đường tròn tâm O bán kính 3 cm và điểm A nằm ngoài đường tròn sao cho "
                 "OA = 5 cm. Từ A kẻ hai tiếp tuyến AB, AC với đường tròn (B, C là tiếp điểm). "
                 "a) Tính AB. b) Chứng minh OA vuông góc với BC.")},
    {"topic": "Bất đẳng thức", "name": "Cauchy",
     "problem": "Cho $a, b > 0$ và $a + b = 2$. Chứng minh rằng $ab \\le 1$."},
]
