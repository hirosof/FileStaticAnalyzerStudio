"""PE 解析器。sniff=lief.is_pe、analyze は段階追加で育つ（まず imphash）。DB は触らない純粋関数。"""
from pathlib import Path

import lief


class PEAnalyzer:
    file_type = "PE"
    result_key = "pe"   # detail_data 内のキー → detail_data["pe"]

    def sniff(self, path: Path) -> bool:
        return lief.is_pe(str(path))

    def analyze(self, path: Path) -> dict:
        binary = lief.parse(str(path))
        if binary is None:
            return {}  # sniff は通ったがパース不可（壊れ等）→ 空（呼び出し側が warn）
        return {
            "imphash": lief.PE.get_imphash(binary, lief.PE.IMPHASH_MODE.PEFILE),
        }