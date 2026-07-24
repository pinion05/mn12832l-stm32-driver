"""메뉴 항목 단일 정의 (코드 리뷰 CODE_REVIEW_20260724_0850 L4/§5.3).

model.py(개수)와 render.py(라벨)에 분산됐던 '3개 항목' 정의를 한 곳으로 통합.
항목 추가/변경 시 이 파일만 고치면 된다.
"""

from __future__ import annotations

from typing import List

# 메인 메뉴 항목 (순서 = 인덱스). model.py와 render.py 모두 이 리스트를 쓴다.
MENU_ITEMS: List[str] = ["MUSIC PLAYER", "MINI GAME", "SETTINGS"]

# 항목 개수 (model.py의 _MAIN_ITEMS 역할)
MENU_ITEM_COUNT: int = len(MENU_ITEMS)
