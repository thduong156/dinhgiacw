def validate_inputs(S, K, T, r, sigma, cr) -> list:
    """
    Kiểm tra tính hợp lệ của các tham số đầu vào.
    Returns: Danh sách lỗi (rỗng = hợp lệ).
    """
    errors = []
    if S is None or S <= 0:
        errors.append("Giá cổ phiếu cơ sở phải lớn hơn 0")
    if K is None or K <= 0:
        errors.append("Giá thực hiện phải lớn hơn 0")
    if T is None or T <= 0:
        errors.append("Thời gian đáo hạn phải lớn hơn 0 (chứng quyền có thể đã hết hạn)")
    if r is None or r < 0:
        errors.append("Lãi suất phi rủi ro không được âm")
    if sigma is None or sigma <= 0:
        errors.append("Biến động giá phải lớn hơn 0%")
    if sigma is not None and sigma > 5.0:
        errors.append("Biến động giá không nên vượt quá 500%")
    if cr is None or cr <= 0:
        errors.append("Tỷ lệ chuyển đổi phải lớn hơn 0")
    return errors


def validate_market_price(cw_price) -> list:
    """Kiểm tra giá CW thị trường."""
    errors = []
    if cw_price is None or cw_price <= 0:
        errors.append("Giá CW thị trường phải lớn hơn 0")
    return errors
