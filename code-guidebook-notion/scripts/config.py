"""공통 설정값.

환경변수로 다른 강의자료 폴더/노션 DB에 재사용 가능:
- METACODE_ROOT: 강의자료 폴더 (PDF 검색 루트)
- METACODE_DB_ID: 노션 DB ID
"""
import os
from pathlib import Path

ROOT = Path(os.environ.get("METACODE_ROOT", r"C:/Users/정화민/Desktop/메타코드"))
OUT_DIR = ROOT / "_output"
IMG_DIR = ROOT / "_split_images"

CONTENT_CACHE = OUT_DIR / "content_cache.json"
EXPLANATIONS = OUT_DIR / "explanations.json"
DRIVE_URLS = OUT_DIR / "drive_urls.json"
NOTION_PAGE_MAP = OUT_DIR / "notion_page_map.json"

# Notion
NOTION_DB_ID = os.environ.get(
    "METACODE_DB_ID",
    "36c734f9-1be4-80b0-8ac9-ed5a0dc670a9",
)
INTEGRATION_NAME = "메타코드"

# Google Drive (rclone remote name)
RCLONE_REMOTE = os.environ.get("RCLONE_REMOTE", "gdrive")
RCLONE_DEST_ROOT = os.environ.get("PDF_DRIVE_DEST", "메타코드/노션이미지")
RCLONE_BIN = os.environ.get("RCLONE_BIN", r"C:\Users\정화민\rclone\rclone.exe")

# 페이지별 강의자료 표시명 매핑 (노션 페이지 제목)
DECK_TITLES = {
    "Sam_이론_5_Pytorch_Fundamentals_Regression_Model":
        "Sam 5강 — PyTorch Fundamentals: Regression Model",
    "Sam_이론_6_Pytorch_Fundamentals_Classification_Model":
        "Sam 6강 — PyTorch Fundamentals: Classification Model",
    "Sam_이론_7_Pytorch_Fundamentals_Vision_Classification":
        "Sam 7강 — PyTorch Fundamentals: Vision Classification",
    "Sam_이론_8_Pytorch_Fundamentals_Time_Series_Model":
        "Sam 8강 — PyTorch Fundamentals: Time Series Model",
    "Sam_이론_9_마무리":
        "Sam 9강 — 마무리",
    "Kim_lesson8_Lesson8_딥러닝1_최종":
        "김동환 Lesson8 — 딥러닝 1",
    # 6주차
    "Liam_Liam_강사님_강의자료_kaggle_실전_머신러닝_강의자료_메타코드M":
        "Liam 강사님 — Kaggle 실전 머신러닝",
    "Sam_이론_1_Introduction_Cource_Welcome":
        "Sam 1강 — Introduction: 강의 환영",
    "Sam_이론_2_Introduction_What_is_Deep_Learning":
        "Sam 2강 — Introduction: What is Deep Learning?",
    "Sam_이론_3_Pytorch_Fundamentals_Neural_Network_학습_(1)":
        "Sam 3강 — PyTorch Fundamentals: Neural Network 학습 (1)",
    "Sam_이론_4_Pytorch_Fundamentals_Neural_Network_학습_(2)":
        "Sam 4강 — PyTorch Fundamentals: Neural Network 학습 (2)",
    # 3주차
    "Kim_데이터의_이해_lesson1_데이터의이해_최종":
        "김동환 Lesson1 — 데이터의 이해",
    "Kim_확률과_통계_Lesson2_확률과통계_최종":
        "김동환 Lesson2 — 확률과 통계",
    "ML_이론_데사_이론1":
        "머신러닝 이론 1 — 데이터사이언스 이론(1)",
    "ML_이론_데사_이론2":
        "머신러닝 이론 2 — 데이터사이언스 이론(2)",
    "ML_머신러닝_강의자료_실습5_basic_classifier_시각화이미지":
        "머신러닝 실습 5 — Basic Classifier 시각화 이미지",
    # 2주차
    "Stat_통계입문올인원_기초통계part1_강의자료_메타코드M":
        "통계 Part1 — 기초통계 강의자료",
    "Stat_통계입문올인원_통계_기초의_모든것_part2_메타코드M":
        "통계 Part2 — 통계 기초의 모든 것",
    # 4주차
    "Kim_lesson3_Lesson3_회귀분석_최종":
        "김동환 Lesson3 — 회귀분석",
    "Kim_lesson4_Lesson4_머신러닝1_최종":
        "김동환 Lesson4 — 머신러닝 1",
    "Bae_배상민_강사님_강의자료_메타코드M_colab_Introduction":
        "배상민 — Colab Introduction",
    "Bae_배상민_강사님_강의자료_메타코드M_머신러닝_1._회귀":
        "배상민 머신러닝 1 — 회귀",
    "Bae_배상민_강사님_강의자료_메타코드M_머신러닝_2._분류":
        "배상민 머신러닝 2 — 분류",
}
