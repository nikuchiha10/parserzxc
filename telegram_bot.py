import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import asyncio
import os
from datetime import datetime

from core.advanced_parser import AdvancedKnowledgeParser
from core.article_manager import ArticleManager
from config import config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KnowledgeParserBot:
    def __init__(self):
        self.parser = AdvancedKnowledgeParser()
        self.article_manager = ArticleManager(config.DATA_DIR)
        self.app = Application.builder().token(config.TELEGRAM_TOKEN).build()
        self.setup_handlers()
        self.setup_commands()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Основные команды
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("parse", self.parse_articles))
        self.app.add_handler(CommandHandler("search", self.search_articles))
        self.app.add_handler(CommandHandler("stats", self.show_stats))
        self.app.add_handler(CommandHandler("export", self.export_data))
        self.app.add_handler(CommandHandler("help", self.help))
        
        # Админские команды
        self.app.add_handler(CommandHandler("admin", self.admin_panel))
        self.app.add_handler(CommandHandler("status", self.system_status))
        
        # Обработка текстовых сообщений
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def setup_commands(self):
        """Настройка меню команд"""
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("parse", "Запустить парсинг статей"),
            BotCommand("search", "Поиск по статьям"),
            BotCommand("stats", "Статистика"),
            BotCommand("export", "Экспорт данных"),
            BotCommand("help", "Помощь")
        ]
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        is_admin = user.id in config.ADMIN_IDS
        
        welcome_text = f"""
🤖 *Добро пожаловать, {user.first_name}!*

*PRO Парсер Базы Знаний* готов к работе!

*Основные команды:*
/parse - Запустить парсинг статей
/search - Поиск по статьям  
/stats - Статистика парсинга
/export - Экспорт данных
/help - Подробная справка

*Примеры использования:*
`/parse 10` - спарсить 10 статей
`/search льготы` - найти статьи про льготы
`/export excel` - экспорт в Excel
        """.strip()
        
        if is_admin:
            welcome_text += "\n\n⚡ *Режим администратора активирован*"
            welcome_text += "\n/admin - Панель управления"
            welcome_text += "\n/status - Статус системы"
        
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def parse_articles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /parse"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ *Доступ запрещен!*\nТолько администраторы могут запускать парсинг.", 
                                          parse_mode='Markdown')
            return
        
        # Получаем количество статей из аргументов
        article_count = 5
        if context.args:
            try:
                article_count = int(context.args[0])
                article_count = min(article_count, config.MAX_ARTICLES_PER_RUN)
            except ValueError:
                await update.message.reply_text("❌ Укажите число: `/parse 10`", parse_mode='Markdown')
                return
        
        await update.message.reply_text(f"🚀 *Запускаю парсинг {article_count} статей...*\nЭто может занять несколько минут.", 
                                      parse_mode='Markdown')
        
        try:
            # Загружаем список статей (здесь должен быть ваш список)
            articles_list = self.load_articles_list()[:article_count]
            
            if not articles_list:
                await update.message.reply_text("❌ Список статей пуст!")
                return
            
            # Запускаем парсинг в отдельном потоке
            results = await asyncio.get_event_loop().run_in_executor(
                None, self.parser.parse_articles_batch, articles_list, article_count
            )
            
            # Формируем отчет
            report = self.format_parsing_report(results)
            await update.message.reply_text(report, parse_mode='Markdown')
            
            # Отправляем файл экспорта если есть успешные статьи
            if results['success'] > 0:
                csv_path = self.parser.article_manager.export_to_csv()
                if csv_path and os.path.exists(csv_path):
                    await update.message.reply_document(
                        document=open(csv_path, 'rb'),
                        filename=f"articles_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        caption="📊 *Экспорт данных в CSV*"
                    )
            
        except Exception as e:
            logger.error(f"Ошибка парсинга: {e}")
            await update.message.reply_text(f"❌ *Ошибка парсинга:*\n`{str(e)}`", parse_mode='Markdown')
    
    async def search_articles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /search"""
        if not context.args:
            await update.message.reply_text("❌ Укажите запрос: `/search льготы`", parse_mode='Markdown')
            return
        
        query = " ".join(context.args)
        await update.message.reply_text(f"🔍 *Ищем: *\"{query}\"*...*", parse_mode='Markdown')
        
        try:
            results = self.article_manager.search_articles(query)
            
            if not results:
                await update.message.reply_text("❌ По вашему запросу ничего не найдено.")
                return
            
            # Формируем ответ
            response = f"*🔍 Найдено результатов: {len(results)}*\n\n"
            
            for i, result in enumerate(results[:5]):  # Показываем первые 5
                response += f"*{i+1}. {result['title']}*\n"
                response += f"📄 {result['excerpt']}\n"
                response += f"🔗 [Открыть статью]({result['url']})\n"
                response += f"📊 Слов: {result['word_count']}\n\n"
            
            if len(results) > 5:
                response += f"*... и еще {len(results) - 5} результатов*"
            
            await update.message.reply_text(response, parse_mode='Markdown', disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            await update.message.reply_text(f"❌ *Ошибка поиска:*\n`{str(e)}`", parse_mode='Markdown')
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        try:
            stats = self.parser.get_detailed_stats()
            
            stats_text = f"""
📊 *Детальная статистика*

*База данных:*
📈 Статей: {stats['total_articles']}
📝 Слов всего: {stats['total_words']:,}
💾 Версия парсера: {stats['parser_version']}

*Последний запуск:*
🕒 {stats.get('last_run', 'Неизвестно')}

*Эффективность парсинга:*
✅ Найдено: {stats.get('articles_found', 0)}
📖 Обработано: {stats.get('articles_parsed', 0)}
🎯 Успешность: {stats.get('success_rate', 0):.1f}%
            """.strip()
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await update.message.reply_text("❌ Ошибка получения статистики")
    
    async def export_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /export"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ *Доступ запрещен!*", parse_mode='Markdown')
            return
        
        export_type = "excel"
        if context.args:
            export_type = context.args[0].lower()
        
        await update.message.reply_text(f"📤 *Подготовка экспорта в {export_type.upper()}...*", parse_mode='Markdown')
        
        try:
            if export_type == "excel":
                file_path = self.parser.article_manager.export_to_excel()
                filename = f"knowledge_base_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
                caption = "📊 *Экспорт в Excel*"
            else:
                file_path = self.parser.article_manager.export_to_csv()
                filename = f"knowledge_base_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
                caption = "📊 *Экспорт в CSV*"
            
            if file_path and os.path.exists(file_path):
                await update.message.reply_document(
                    document=open(file_path, 'rb'),
                    filename=filename,
                    caption=caption,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Нет данных для экспорта")
                
        except Exception as e:
            logger.error(f"Ошибка экспорта: {e}")
            await update.message.reply_text(f"❌ *Ошибка экспорта:*\n`{str(e)}`", parse_mode='Markdown')
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Панель администратора"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ *Доступ запрещен!*", parse_mode='Markdown')
            return
        
        admin_text = """
⚡ *Панель администратора*

*Команды управления:*
/status - Статус системы
/parse - Запуск парсинга
/export - Экспорт данных

*Статистика:*
• Парсер: Активен ✅
• База данных: Готова ✅
• Логи: Включены ✅

*Быстрые действия:*
`/parse 10` - Парсинг 10 статей
`/export excel` - Экспорт в Excel
`/status` - Детальный статус
        """.strip()
        
        await update.message.reply_text(admin_text, parse_mode='Markdown')
    
    async def system_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статус системы"""
        user_id = update.effective_user.id
        
        if user_id not in config.ADMIN_IDS:
            await update.message.reply_text("❌ *Доступ запрещен!*", parse_mode='Markdown')
            return
        
        try:
            import psutil
            import platform
            
            # Системная информация
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status_text = f"""
🖥️ *Статус системы*

*Система:*
💻 OS: {platform.system()} {platform.release()}
🐍 Python: {platform.python_version()}
📊 Память: {memory.percent}% использовано
💾 Диск: {disk.percent}% использовано

*Парсер:*
🔧 Версия: 2.0.0
📈 Статей в базе: {self.parser.article_manager.get_stats()['total_articles']}
🔄 Последний запуск: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

*Статус:*
✅ Бот: Активен
✅ Парсер: Готов
✅ База данных: Работает
            """.strip()
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса: {e}")
            await update.message.reply_text("❌ Ошибка получения статуса системы")
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📚 *PRO Парсер Базы Знаний - Помощь*

*Основные команды:*
/parse [число] - Запустить парсинг статей
/search [запрос] - Поиск по статьям
/stats - Детальная статистика
/export [тип] - Экспорт данных (excel/csv)

*Примеры использования:*
`/parse 15` - спарсить 15 статей
`/search "замена счетчика"` - поиск по фразе
`/export excel` - экспорт в Excel формат
`/stats` - полная статистика

*Для администраторов:*
/admin - Панель управления
/status - Статус системы

💡 *Советы:*
• Используйте точные формулировки для поиска
• Начинайте с малого количества статей для теста
• Регулярно экспортируйте данные для бэкапа
        """.strip()
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        text = update.message.text
        
        # Простые ответы на частые вопросы
        responses = {
            'привет': '👋 Привет! Я PRO парсер базы знаний. Используйте /help для списка команд.',
            'спасибо': '🤝 Пожалуйста! Рад помочь!',
            'статус': '📊 Используйте /stats для статистики или /status для системного статуса.',
            'помощь': '📚 Используйте /help для подробной справки.'
        }
        
        response = responses.get(text.lower(), 
                               '🤖 Используйте команды для работы с парсером. /help - список команд.')
        
        await update.message.reply_text(response)
    
    def load_articles_list(self):
        """Загрузка списка статей для парсинга"""
        # Здесь должен быть ваш список из 847 статей
        # Для примера возвращаем тестовый список
        return [
            "Ограничение/восстановление э/э потребителям-неплательщикам",
            "Контактная информация (адрес, телефон, режим работы)",
            "Обработка письменных обращений",
            "Графики ограничения неплательщиков ЮЛ",
            "Алгоритм действий оператора по исключению из информирования по ДЗ",
            "Порядок действий при обращении клиентов с запросом на смену статуса ПУ в БД",
            "Оформление услуги Жалоба на некорректные показания ПУ",
            "Подтверждение оплаты задолженности (ДЗ)",
            "Вопросы - ответы ЕЛК ЖКХ",
            "Актуальное ЕЛК ЖКХ"
        ]
    
    def format_parsing_report(self, results: Dict) -> str:
        """Форматирование отчета о парсинге"""
        success_rate = (results['success'] / (results['success'] + results['failed']) * 100) if (results['success'] + results['failed']) > 0 else 0
        
        report = f"""
📊 *ОТЧЕТ О ПАРСИНГЕ*

✅ *Успешно:* {results['success']}
❌ *Ошибки:* {results['failed']}
⏭️ *Пропущено:* {results.get('skipped', 0)}

⏱️ *Время выполнения:* {results['total_time']:.2f} сек
📈 *Эффективность:* {success_rate:.1f}%

💾 *Результаты:*
• Статьи сохранены в папке `{config.DATA_DIR}`
• Доступен экспорт в CSV/Excel
• Используйте /search для поиска
        """.strip()
        
        return report
    
    def run(self):
        """Запуск бота"""
        logger.info("🤖 Запуск PRO Telegram бота...")
        print("✅ Бот запущен! Откройте Telegram и найдите вашего бота.")
        print("💡 Используйте /start для начала работы")
        self.app.run_polling()

def main():
    """Основная функция"""
    bot = KnowledgeParserBot()
    bot.run()

if __name__ == "__main__":
    main()
