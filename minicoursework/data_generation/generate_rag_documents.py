"""
==============================================================================
MÔ TẢ FILE: data_generation/generate_rag_documents.py
------------------------------------------------------------------------------
Tự động sinh tài liệu tri thức E-Commerce (Chính sách đổi trả, Bảo hành,
Vận chuyển, Hướng dẫn sản phẩm) phục vụ cho RAG Data Pipeline.
==============================================================================
"""

import os
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "data" / "rag_documents"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DOCUMENTS = [
    {
        "doc_id": "DOC_POL_001",
        "title": "Chính Sách Đổi Trả và Hoàn Tiền E-Commerce 2026",
        "category": "Policy",
        "content": (
            "Khách hàng có quyền yêu cầu đổi trả sản phẩm trong vòng 30 ngày kể từ ngày nhận hàng. "
            "Điều kiện đổi trả: Sản phẩm phải còn nguyên tem mác, chưa qua sử dụng và đầy đủ phụ kiện kèm theo. "
            "Các trường hợp sản phẩm lỗi do nhà sản xuất hoặc giao sai mẫu mã sẽ được miễn phí 100% cước phí vận chuyển đổi trả. "
            "Tiền hoàn sẽ được chuyển về tài khoản ngân hàng hoặc ví điện tử của khách hàng trong vòng 3-5 ngày làm việc "
            "kể từ khi kho nhận lại và kiểm tra hàng thành công."
        )
    },
    {
        "doc_id": "DOC_POL_002",
        "title": "Chính Sách Vận Chuyển và Giao Hàng Hỏa Tốc",
        "category": "Policy",
        "content": (
            "Sàn thương mại điện tử hỗ trợ giao hàng hỏa tốc trong 2 giờ đối với các đơn hàng tại khu vực nội thành Hà Nội "
            "và TP. Hồ Chí Minh. Đối với giao hàng tiêu chuẩn, thời gian vận chuyển từ 2 đến 4 ngày làm việc trên toàn quốc. "
            "Đơn hàng có tổng giá trị thanh toán từ 500.000 VNĐ trở lên sẽ được miễn phí vận chuyển tối đa 30.000 VNĐ. "
            "Khách hàng có thể đồng kiểm (kiểm tra ngoại quan) cùng nhân viên giao hàng trước khi thanh toán đối với đơn hàng COD."
        )
    },
    {
        "doc_id": "DOC_POL_003",
        "title": "Chính Sách Bảo Hành Điện Tử và Hỗ Trợ Kỹ Thuật",
        "category": "Support",
        "content": (
            "Tất cả các sản phẩm thiết bị điện tử, đồ gia dụng công nghệ bán ra đều được áp dụng bảo hành điện tử chính hãng "
            "từ 12 đến 24 tháng dựa trên mã IMEI hoặc số Seri. Khách hàng chỉ cần đọc số điện thoại đặt hàng để làm thủ tục bảo hành "
            "tại bất kỳ trung tâm ủy quyền nào trên toàn quốc. Trong 30 ngày đầu tiên nếu máy có lỗi phần cứng từ nhà sản xuất, "
            "khách hàng sẽ được đổi mới 1-đổi-1 ngay lập tức mà không mất thêm chi phí."
        )
    },
    {
        "doc_id": "DOC_PROD_001",
        "title": "Hướng Dẫn Sản Phẩm: Điện Thoại Flagship Pro Max 2026",
        "category": "ProductGuide",
        "content": (
            "Điện thoại Flagship Pro Max được trang bị vi xử lý 3nm thế hệ mới, màn hình OLED 120Hz siêu nét "
            "và cụm camera cảm biến 200MP hỗ trợ chụp đêm AI. Sản phẩm trang bị viên pin 5000mAh hỗ trợ sạc nhanh 100W "
            "giúp sạc đầy 80% chỉ trong 15 phút. Thiết bị đạt chuẩn chống nước và bụi bẩn IP68, mặt lưng kính cường lực "
            "chống va đập vượt trội. Phù hợp cho người dùng cần hiệu năng đồ họa cao và sáng tạo nội dung chuyên nghiệp."
        )
    },
    {
        "doc_id": "DOC_PROD_002",
        "title": "Hướng Dẫn Sản Phẩm: Tai Nghe Chống Ồn Chủ Động ANC Wireless",
        "category": "ProductGuide",
        "content": (
            "Tai nghe ANC Wireless sở hữu công nghệ chống ồn chủ động thích ứng thế hệ 5, loại bỏ đến 98% tiếng ồn môi trường xung quanh. "
            "Thời lượng pin nghe liên tục lên đến 40 giờ khi tắt ANC và 30 giờ khi bật ANC. Hỗ trợ kết nối Bluetooth 5.4 đa điểm "
            "cho phép chuyển đổi mượt mà giữa điện thoại và máy tính. Đạt chuẩn kháng nước IPX4 thích hợp tập luyện thể thao."
        )
    }
]

def main():
    print(f"🚀 Generating {len(DOCUMENTS)} RAG knowledge documents to {OUTPUT_DIR}...")
    for doc in DOCUMENTS:
        file_path = OUTPUT_DIR / f"{doc['doc_id']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"   - Generated: {file_path.name}")
    print("✅ RAG Knowledge Documents generated successfully!")

if __name__ == "__main__":
    main()
