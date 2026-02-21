import pandas as pd
from datetime import date


REQUIRED_COLUMNS = [
    "ma_cw",            # Mã CW (vd: CVPB2401)
    "ma_co_so",         # Mã cổ phiếu cơ sở (vd: VPB)
    "gia_co_so",        # Giá cổ phiếu cơ sở
    "gia_thuc_hien",    # Giá thực hiện (strike)
    "ngay_dao_han",     # Ngày đáo hạn (DD/MM/YYYY)
    "ty_le_chuyen_doi", # Tỷ lệ chuyển đổi
    "gia_cw",           # Giá CW thị trường
    "loai_cw",          # "call" hoặc "put"
]

OPTIONAL_COLUMNS = [
    "lai_suat_phi_rui_ro",  # Lãi suất phi rủi ro (default 0.03)
    "bien_do_gia",          # Biến động giá (nếu đã biết)
]


def validate_csv(df: pd.DataFrame) -> tuple:
    """
    Kiểm tra CSV có đủ cột bắt buộc.
    Returns: (is_valid, list_of_errors)
    """
    errors = []

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            errors.append(f"Thiếu cột bắt buộc: '{col}'")

    if errors:
        return False, errors

    # Kiểm tra dữ liệu
    numeric_cols = ["gia_co_so", "gia_thuc_hien", "ty_le_chuyen_doi", "gia_cw"]
    for col in numeric_cols:
        if df[col].isna().any():
            na_rows = df[df[col].isna()].index.tolist()
            errors.append(f"Cột '{col}' có giá trị trống tại dòng {na_rows}")
        try:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        except Exception:
            errors.append(f"Cột '{col}' chứa giá trị không phải số")
            continue
        if (df[col] <= 0).any():
            errors.append(f"Cột '{col}' phải chứa giá trị dương")

    valid_types = ["call", "put"]
    invalid = df[~df["loai_cw"].str.lower().isin(valid_types)]
    if len(invalid) > 0:
        errors.append(f"Cột 'loai_cw' chỉ chấp nhận 'call' hoặc 'put' (dòng {invalid.index.tolist()})")

    return len(errors) == 0, errors


def parse_csv(uploaded_file) -> tuple:
    """
    Đọc và xử lý file CSV.
    Returns: (DataFrame, list_of_warnings) hoặc (None, list_of_errors)
    """
    # Thử đọc với nhiều encoding
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding="latin-1")
        except Exception as e:
            return None, [f"Không thể đọc file CSV: {str(e)}"]
    except Exception as e:
        return None, [f"Lỗi đọc file CSV: {str(e)}"]

    # Chuẩn hóa tên cột
    df.columns = df.columns.str.strip().str.lower()

    is_valid, errors = validate_csv(df)
    if not is_valid:
        return None, errors

    warnings = []

    # Chuyển đổi ngày - hỗ trợ nhiều format
    try:
        df["ngay_dao_han"] = pd.to_datetime(
            df["ngay_dao_han"], format="%d/%m/%Y"
        )
    except (ValueError, TypeError):
        try:
            df["ngay_dao_han"] = pd.to_datetime(
                df["ngay_dao_han"], dayfirst=True
            )
            warnings.append(
                "Ngày đáo hạn không đúng format DD/MM/YYYY, đã tự động nhận diện."
            )
        except Exception:
            return None, [
                "Không thể chuyển đổi cột 'ngay_dao_han'. "
                "Hãy sử dụng định dạng DD/MM/YYYY (VD: 30/06/2026)"
            ]

    today = pd.Timestamp(date.today())
    df["T"] = (df["ngay_dao_han"] - today).dt.days / 365.0

    # Cảnh báo nếu có CW đã hết hạn
    expired = df[df["T"] <= 0]
    if len(expired) > 0:
        expired_names = expired["ma_cw"].tolist()
        warnings.append(
            f"Các CW đã hết hạn hoặc đáo hạn hôm nay: {expired_names}. "
            f"Sẽ tính với T tối thiểu = 0.001 năm."
        )

    df["T"] = df["T"].clip(lower=0.001)

    # Chuẩn hóa loại CW
    df["loai_cw"] = df["loai_cw"].str.lower().str.strip()

    # Default values
    if "lai_suat_phi_rui_ro" not in df.columns:
        df["lai_suat_phi_rui_ro"] = 0.03
    if "bien_do_gia" not in df.columns:
        df["bien_do_gia"] = 0.30

    return df, warnings
