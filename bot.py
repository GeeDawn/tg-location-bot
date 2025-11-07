import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, filters
)
from config import BOT_TOKEN, ADMIN_IDS, DEFAULT_LOCATION
from database import Database
from utils import is_in_range, format_location_message, calculate_distance

# 初始化数据库
db = Database()

# 设置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def is_admin(user_id: int) -> bool:
    """检查用户是否为管理员"""
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始命令"""
    user = update.effective_user
    
    # 获取全局设置
    settings = db.get_global_location_settings()
    
    welcome_text = (
        f"👋 你好 {user.first_name}!\n\n"
        "🤖 我是一个位置验证机器人\n\n"
        "📍 主要功能:\n"
        "• 验证您的位置是否在指定范围内\n"
        "\n"
        # "• 管理员可以设置全局位置范围\n\n"
    )
    
    # if settings:
    #     welcome_text += (
    #         f"📋 当前全局验证区域:\n"
    #         f"• 中心点: {settings['latitude']:.4f}, {settings['longitude']:.4f}\n"
    #         f"• 范围: {settings['radius']} 米\n"
    #         f"• 设置者: {settings['set_by_username'] or '管理员'}\n\n"
    #     )
    # else:
    #     welcome_text += "⚠️ 尚未设置位置范围，请联系管理员\n\n"
    
    welcome_text += (
        "📌 使用方法:\n"
        "• 点击下方按钮分享位置\n"
        # "• 或发送 /check 开始验证\n\n"
        # "⚙️ 管理员命令:\n"
        # "• /setlocation - 设置全局位置范围\n"
        # "• /settings - 查看当前设置\n"
        # "• /stats - 查看验证统计"
    )
    
    # 创建位置分享键盘
    keyboard = [
        [KeyboardButton("📍 分享位置", request_location=True)]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def check_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """请求位置验证"""
    settings = db.get_global_location_settings()
    
    if not settings:
        await update.message.reply_text(
            "❌ 尚未设置位置范围，请联系管理员使用 /setlocation 命令进行设置"
        )
        return
    
    keyboard = [
        [KeyboardButton("📍 分享位置", request_location=True)]
    ]
    reply_markup = ReplyKeyboardMarkup(
        keyboard, 
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await update.message.reply_text(
        f"📍 请分享您的位置进行验证\n\n",
        # f"当前全局验证区域:\n"
        # f"• 中心: {settings['latitude']:.4f}, {settings['longitude']:.4f}\n"
        # f"• 半径: {settings['radius']} 米\n"
        # f"• 对所有用户生效"
        
        reply_markup=reply_markup
    )

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理用户发送的位置"""
    user = update.effective_user
    location = update.message.location
    
    # 获取全局位置设置
    settings = db.get_global_location_settings()
    if not settings:
        await update.message.reply_text(
            "❌ 尚未设置位置范围，请联系管理员使用 /setlocation 命令进行设置"
        )
        return
    
    user_coords = (location.latitude, location.longitude)
    target_coords = (settings['latitude'], settings['longitude'])
    
    # 检查是否在范围内
    in_range = is_in_range(user_coords, target_coords, settings['radius'])
    distance = calculate_distance(user_coords, target_coords)
    
    # 保存验证记录
    db.save_user_check(
        user_id=user.id,
        username=user.username or user.first_name,
        latitude=location.latitude,
        longitude=location.longitude,
        is_in_range=in_range
    )
    
    # 发送结果
    message = format_location_message(
        location.latitude, 
        location.longitude, 
        in_range, 
        distance
    )
    
    # 添加范围信息
    message += f"\n📏 设定范围: {settings['radius']} 米"
    
    await update.message.reply_text(message)

async def set_location_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """设置全局位置范围命令"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限执行此操作")
        return
    
    if len(context.args) != 3:
        help_text = (
            "📌 设置全局位置范围\n\n"
            "使用方法: /setlocation <纬度> <经度> <半径(米)>\n\n"
            "例如: /setlocation 40.7128 -74.0060 1000\n\n"
            "📍 这将设置以指定坐标为中心，半径1000米的验证范围\n"
            "⚠️ 此设置对所有用户生效，无论他们在哪个聊天中使用机器人"
        )
        await update.message.reply_text(help_text)
        return
    
    try:
        latitude = float(context.args[0])
        longitude = float(context.args[1])
        radius = int(context.args[2])
        
        # 验证坐标范围
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            await update.message.reply_text("❌ 坐标范围无效\n纬度范围: -90 到 90\n经度范围: -180 到 180")
            return
        
        if radius <= 0:
            await update.message.reply_text("❌ 半径必须为正数")
            return
        
        if radius > 50000:  # 限制最大半径为50公里
            await update.message.reply_text("❌ 半径不能超过50公里")
            return
        
        # 保存全局设置
        user = update.effective_user
        db.set_global_location_settings(
            latitude, longitude, radius, 
            user.id, 
            user.username or user.first_name
        )
        
        await update.message.reply_text(
            f"✅ 全局位置范围设置成功!\n\n"
            f"📋 新的验证区域:\n"
            f"• 中心点: {latitude:.6f}, {longitude:.6f}\n"
            f"• 半径: {radius} 米\n\n"
            f"🌍 此设置对所有用户生效\n"
            f"📍 所有用户的位置验证将基于此范围"
        )
        
    except ValueError:
        await update.message.reply_text("❌ 参数格式错误，请确保输入正确的数字")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看当前全局设置"""
    settings = db.get_global_location_settings()
    
    if not settings:
        message = (
            "📋 当前位置设置:\n\n"
            "❌ 尚未设置位置范围\n\n"
            "请管理员使用 /setlocation 命令进行设置\n"
            "例如: /setlocation 40.7128 -74.0060 1000"
        )
    else:
        message = (
            "🌍 全局位置设置:\n\n"
            f"• 中心纬度: {settings['latitude']:.6f}\n"
            f"• 中心经度: {settings['longitude']:.6f}\n"
            f"• 范围半径: {settings['radius']} 米\n"
            f"• 设置者: {settings['set_by_username'] or '管理员'}\n"
            f"• 更新时间: {settings['updated_at'][:16] if settings['updated_at'] else '未知'}\n\n"
            "📍 所有用户的位置验证将基于此范围"
        )
    
    await update.message.reply_text(message)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查看统计信息"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ 您没有权限执行此操作")
        return
    
    settings = db.get_global_location_settings()
    stats = db.get_verification_stats()
    
    if not settings:
        await update.message.reply_text("❌ 尚未设置位置范围")
        return
    
    if stats['total_checks'] > 0:
        pass_rate = (stats['passed_checks'] / stats['total_checks']) * 100
    else:
        pass_rate = 0
    
    message = (
        "📊 全局验证统计\n\n"
        f"📍 当前设置:\n"
        f"• 中心点: {settings['latitude']:.6f}, {settings['longitude']:.6f}\n"
        f"• 半径: {settings['radius']} 米\n\n"
        f"📈 验证数据:\n"
        f"• 总验证次数: {stats['total_checks']}\n"
        f"• 通过次数: {stats['passed_checks']}\n"
        f"• 通过率: {pass_rate:.1f}%\n"
        f"• 最近24小时: {stats['recent_checks']} 次\n\n"
        f"🌍 全局生效，所有用户共享同一设置"
    )
    
    await update.message.reply_text(message)

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员帮助"""
    if not is_admin(update.effective_user.id):
        return
    
    help_text = (
        "👨‍💼 管理员命令:\n\n"
        "• /setlocation <lat> <lon> <radius> - 设置全局位置范围\n"
        "• /settings - 查看当前设置\n"
        "• /stats - 查看验证统计\n"
        "• /adminhelp - 显示此帮助信息\n\n"
        "📍 示例:\n"
        "/setlocation 40.7128 -74.0060 500\n\n"
        "⚠️ 注意: 设置的全局位置范围对所有用户生效，无论他们在私聊还是群组中使用机器人"
    )
    
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理文本消息"""
    message_text = update.message.text
    
    if message_text == "📍 分享位置":
        await check_location(update, context)
    else:
        await update.message.reply_text(
            "请使用 /start 查看功能说明，或使用 /check 开始位置验证"
        )

def main():
    """启动机器人"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 添加处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check", check_location))
    application.add_handler(CommandHandler("setlocation", set_location_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("adminhelp", admin_help))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # 启动机器人
    print("🤖 全局位置验证机器人已启动...")
    application.run_polling()

if __name__ == '__main__':
    main()