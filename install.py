#!/usr/bin/env python3
"""
Скрипт автоматической установки PRO Knowledge Parser
"""

import os
import sys
import subprocess
import platform

def run_command(command, check=True):
    """Выполнение команды в shell"""
    print(f"🛠️ Выполняю: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e}")
        return False

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Устанавливаю зависимости...")
    
    # Обновляем pip
    run_command("pip install --upgrade pip")
    
    # Устанавливаем зависимости
    if run_command("pip install -r requirements.txt"):
        print("✅ Зависимости установлены успешно")
        return True
    else:
        print("❌ Ошибка установки зависимостей")
        return False

def setup_directories():
    """Создание необходимых директорий"""
    print("📁 Создаю структуру директорий...")
    
    directories = ['data', 'logs', 'backups', 'core']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Создана директория: {directory}")
    
    print("✅ Структура директорий создана")

def check_chrome_driver():
    """Проверка Chrome Driver"""
    print("🔍 Проверяю Chrome Driver...")
    
    system = platform.system().lower()
    
    if system == "linux":
        # Для Ubuntu/Debian
        if run_command("which google-chrome", check=False):
            print("✅ Chrome установлен")
        else:
            print("⚠️ Chrome не установлен. Установите:")
            print("  sudo apt update && sudo apt install google-chrome-stable")
    
    elif system == "windows":
        print("✅ Windows - Chrome Driver будет установлен автоматически")
    
    elif system == "darwin":  # macOS
        if run_command("which google-chrome", check=False):
            print("✅ Chrome установлен")
        else:
            print("⚠️ Установите Chrome с официального сайта")
    
    return True

def create_env_file():
    """Создание .env файла если его нет"""
    if not os.path.exists('.env'):
        print("🔧 Создаю файл .env...")
        
        env_content = """# PRO Knowledge Parser Configuration

# Telegram Bot
TELEGRAM_TOKEN=7220498387:AAEPlB9BLtTdmzUtRoD2pXhsoB3UzsnoMzE

# Website Auth (если требуется)
KMS_USERNAME=your_username
KMS_PASSWORD=your_password

# Parser Settings
MAX_ARTICLES_PER_RUN=50
REQUEST_DELAY=1
"""
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("✅ Файл .env создан. Отредактируйте его при необходимости.")

def main():
    """Основная функция установки"""
    print("🚀 PRO Knowledge Parser - Установка")
    print("=" * 50)
    
    # Проверяем Python версию
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    print(f"✅ ОС: {platform.system()} {platform.release()}")
    
    # Выполняем установку
    setup_directories()
    
    if not install_dependencies():
        print("❌ Установка прервана из-за ошибок")
        sys.exit(1)
    
    check_chrome_driver()
    create_env_file()
    
    print("\n🎉 Установка завершена успешно!")
    print("\n📚 Дальнейшие действия:")
    print("1. Отредактируйте .env файл при необходимости")
    print("2. Запустите бота: python main.py --mode bot")
    print("3. Или протестируйте парсер: python main.py --mode parser")
    print("4. Для справки: python main.py --help")

if __name__ == "__main__":
    main()
