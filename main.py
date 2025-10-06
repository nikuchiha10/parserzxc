#!/usr/bin/env python3
"""
PRO Knowledge Parser - Профессиональный парсер базы знаний
"""

import argparse
import sys
import os
from telegram_bot import KnowledgeParserBot
from core.advanced_parser import AdvancedKnowledgeParser
from core.article_manager import ArticleManager
from config import config

def run_parser_demo():
    """Демонстрация работы парсера"""
    print("🚀 PRO Knowledge Parser - Демонстрационный режим")
    print("=" * 50)
    
    parser = AdvancedKnowledgeParser()
    
    # Тестовые статьи для демонстрации
    test_articles = [
        "Ограничение/восстановление э/э потребителям-неплательщикам",
        "Контактная информация (адрес, телефон, режим работы)",
        "Обработка письменных обращений"
    ]
    
    try:
        print("🎯 Запуск парсинга тестовых статей...")
        results = parser.parse_articles_batch(test_articles, max_articles=2)
        
        print("\n📊 Результаты:")
        print(f"✅ Успешно: {results['success']}")
        print(f"❌ Ошибки: {results['failed']}")
        print(f"⏱️ Время: {results['total_time']:.2f} сек")
        
        if results['success'] > 0:
            print("💾 Данные сохранены в папке data/")
            print("📊 Доступен экспорт через Telegram бота")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        parser.close()

def run_telegram_bot():
    """Запуск Telegram бота"""
    print("🤖 Запуск PRO Telegram бота...")
    bot = KnowledgeParserBot()
    bot.run()

def show_system_info():
    """Показать информацию о системе"""
    print("🖥️ PRO Knowledge Parser - Информация о системе")
    print("=" * 50)
    
    # Проверяем зависимости
    try:
        import selenium
        import pandas
        import aiohttp
        print("✅ Все зависимости установлены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        return
    
    # Проверяем конфигурацию
    print(f"🔧 Конфигурация:")
    print(f"   • База URL: {config.BASE_URL}")
    print(f"   • Данные: {config.DATA_DIR}")
    print(f"   • Логи: {config.LOGS_DIR}")
    print(f"   • Макс. статей: {config.MAX_ARTICLES_PER_RUN}")
    
    # Проверяем данные
    manager = ArticleManager(config.DATA_DIR)
    stats = manager.get_stats()
    print(f"📊 База данных: {stats['total_articles']} статей")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='PRO Knowledge Parser')
    parser.add_argument('--mode', choices=['bot', 'parser', 'info'], default='info',
                       help='Режим работы: bot - Telegram бот, parser - демо парсера, info - информация о системе')
    parser.add_argument('--articles', type=int, default=3,
                       help='Количество статей для парсинга (только для режима parser)')
    
    args = parser.parse_args()
    
    if args.mode == 'bot':
        run_telegram_bot()
    elif args.mode == 'parser':
        run_parser_demo()
    else:
        show_system_info()

if __name__ == "__main__":
    main()
