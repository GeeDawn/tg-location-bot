import sqlite3
import json
from typing import Optional, Dict, Any

class Database:
    def __init__(self, db_path='bot_data.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 全局位置设置
            conn.execute('''
                CREATE TABLE IF NOT EXISTS global_location_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    latitude REAL,
                    longitude REAL,
                    radius INTEGER,
                    set_by INTEGER,  -- 设置的管理员ID
                    set_by_username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 用户验证记录
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    latitude REAL,
                    longitude REAL,
                    is_in_range BOOLEAN,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 插入默认设置（如果不存在）
            cursor = conn.execute('SELECT COUNT(*) FROM global_location_settings')
            if cursor.fetchone()[0] == 0:
                conn.execute('''
                    INSERT INTO global_location_settings 
                    (latitude, longitude, radius, set_by, set_by_username) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (40.7128, -74.0060, 1000, 0, 'system'))
    
    def get_global_location_settings(self) -> Optional[Dict[str, Any]]:
        """获取全局位置设置"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                'SELECT latitude, longitude, radius, set_by, set_by_username, updated_at FROM global_location_settings ORDER BY id DESC LIMIT 1'
            )
            result = cursor.fetchone()
            if result:
                return {
                    'latitude': result[0],
                    'longitude': result[1],
                    'radius': result[2],
                    'set_by': result[3],
                    'set_by_username': result[4],
                    'updated_at': result[5]
                }
            return None
    
    def set_global_location_settings(self, latitude: float, longitude: float, radius: int, set_by: int, set_by_username: str):
        """设置全局位置范围"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO global_location_settings 
                (latitude, longitude, radius, set_by, set_by_username, updated_at) 
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (latitude, longitude, radius, set_by, set_by_username))
    
    def save_user_check(self, user_id: int, username: str, latitude: float, longitude: float, is_in_range: bool):
        """保存用户验证记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO user_checks 
                (user_id, username, latitude, longitude, is_in_range)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, latitude, longitude, is_in_range))
    
    def get_verification_stats(self):
        """获取验证统计"""
        with sqlite3.connect(self.db_path) as conn:
            # 总验证次数
            total_cursor = conn.execute('SELECT COUNT(*) FROM user_checks')
            total = total_cursor.fetchone()[0]
            
            # 通过次数
            passed_cursor = conn.execute('SELECT COUNT(*) FROM user_checks WHERE is_in_range = 1')
            passed = passed_cursor.fetchone()[0]
            
            # 最近24小时验证次数
            recent_cursor = conn.execute(
                'SELECT COUNT(*) FROM user_checks WHERE checked_at > datetime("now", "-1 day")'
            )
            recent = recent_cursor.fetchone()[0]
            
            return {
                'total_checks': total,
                'passed_checks': passed,
                'recent_checks': recent
            }