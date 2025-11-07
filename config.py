import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []

# 默认位置范围（纬度，经度，半径米）
DEFAULT_LOCATION = {
    'latitude': 34.78083,  # 纽约
    'longitude': 113.81944,
    'radius': 1000  # 1公里
}