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
        
        with open('.env', 'w', encoding='
