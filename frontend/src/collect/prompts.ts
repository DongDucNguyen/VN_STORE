// Câu mẫu cho phiên thu âm benchmark voice (PLAN.md mục 6.2): tên thương hiệu, địa danh/làng nghề,
// từ thủ công, giá, đơn vị, phủ định, câu tự nhiên, xen tiếng Anh, nhu cầu ngoài catalog.
// Người nói đọc tự nhiên; người duyệt nghe lại và sửa reference_text nếu người nói đọc khác câu mẫu.
// Sửa/thêm câu ở đây; giữ id cũ ổn định để không lẫn bản ghi giữa các phiên.
export interface Prompt {
  id: string;
  text: string;
  tags: string[];
}

export const PROMPTS: Prompt[] = [
  { id: "p01", text: "tìm cho mình cái túi cói dưới ba trăm nghìn", tags: ["price", "natural"] },
  { id: "p02", text: "bình gốm Bát Tràng dưới năm trăm nghìn", tags: ["place", "price"] },
  { id: "p03", text: "giỏ mây đan có quai", tags: ["material"] },
  { id: "p04", text: "giỏ đan không lấy nhựa", tags: ["negation"] },
  { id: "p05", text: "bình hoa Minh Long", tags: ["brand"] },
  { id: "p06", text: "bộ trà sứ Minh Long khoảng một triệu", tags: ["brand", "price"] },
  { id: "p07", text: "sô cô la Marou Bến Tre", tags: ["brand", "place"] },
  { id: "p08", text: "sô cô la đen trên một trăm nghìn", tags: ["price"] },
  { id: "p09", text: "áo khoác nhuộm chàm của Kilomet một trăm linh chín", tags: ["brand", "craft"] },
  { id: "p10", text: "váy lụa nhuộm tự nhiên", tags: ["material", "craft"] },
  { id: "p11", text: "chụp đèn đan seagrass", tags: ["code_switch", "material"] },
  { id: "p12", text: "túi lục bình đan tay đính vỏ sò", tags: ["material", "craft"] },
  { id: "p13", text: "khay mây đan tay để bàn", tags: ["material"] },
  { id: "p14", text: "bát tre cuộn phủ sơn mài", tags: ["material", "craft"] },
  { id: "p15", text: "hộp sơn mài Hanoia", tags: ["brand", "craft"] },
  { id: "p16", text: "chén cơm sứ trắng dưới một trăm nghìn", tags: ["price"] },
  { id: "p17", text: "ly sứ có nắp không lấy màu đỏ", tags: ["negation"] },
  { id: "p18", text: "quà tặng mẹ làm thủ công từ hai trăm đến năm trăm nghìn", tags: ["price", "natural"] },
  { id: "p19", text: "đồ gốm men lam vẽ sen", tags: ["craft"] },
  { id: "p20", text: "một triệu rưỡi mua được bình hoa nào", tags: ["price", "natural"] },
  { id: "p21", text: "vòng cổ vải handmade", tags: ["code_switch"] },
  { id: "p22", text: "trà Thái Nguyên nửa ký", tags: ["place", "unit"] },
  { id: "p23", text: "khăn lụa Vạn Phúc màu xanh", tags: ["place", "material"] },
  { id: "p24", text: "nồi cơm điện giá rẻ", tags: ["out_of_catalog"] },
];
