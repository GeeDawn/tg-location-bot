from geopy.distance import geodesic
from typing import Tuple

def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """计算两点之间的距离（米）"""
    return geodesic(point1, point2).meters

def is_in_range(user_location: Tuple[float, float], 
                target_location: Tuple[float, float], 
                radius: float) -> bool:
    """检查用户位置是否在目标范围内"""
    distance = calculate_distance(user_location, target_location)
    return distance <= radius

def format_location_message(latitude: float, longitude: float, is_in_range: bool, distance: float = None) -> str:
    """格式化位置验证结果消息"""
    status = "✅ 在范围内" if is_in_range else "❌ 不在范围内"
    message = f"📍 位置验证结果:\n\n"
    message += f"• 纬度: {latitude:.6f}\n"
    message += f"• 经度: {longitude:.6f}\n"
    message += f"• 状态: {status}\n"
    
    if distance is not None:
        message += f"• 距离中心点: {distance:.2f} 米\n"
    
    return message