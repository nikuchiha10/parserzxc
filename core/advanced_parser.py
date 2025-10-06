import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
import logging
import time
from .parser_engine import ParserEngine, Article
from .article_manager import ArticleManager
from config import config

class AdvancedKnowledgeParser:
    def __init__(self):
        self.parser_engine = ParserEngine(config)
        self.article_manager = ArticleManager(config.DATA_DIR)
        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_REQUESTS)
        
    def parse_articles_batch(self, articles_list: List[str], max_articles: int = None) -> Dict:
        """Пакетный парсинг статей с продвинутой логикой"""
        self.logger.info(f"🚀 Запуск пакетного парсинга {len(articles_list)} статей")
        
        start_time = time.time()
        results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total_time': 0,
            'articles': []
        }
        
        try:
            # Инициализация браузера
            self.parser_engine.init_selenium()
            
            # Авторизация
            if not self.parser_engine.smart_login():
                self.logger.error("❌ Не удалось авторизоваться")
                return results
            
            # Ограничиваем количество статей если нужно
            articles_to_parse = articles_list
            if max_articles:
                articles_to_parse = articles_list[:max_articles]
            
            self.logger.info(f"🎯 Будет обработано {len(articles_to_parse)} статей")
            
            # Парсим статьи
            for i, article_title in enumerate(articles_to_parse):
                self.logger.info(f"\n--- [{i+1}/{len(articles_to_parse)}] {article_title} ---")
                
                try:
                    # Поиск статьи
                    search_results = self.parser_engine.search_articles(article_title)
                    
                    if not search_results:
                        self.logger.warning(f"⚠️ Статья не найдена: {article_title}")
                        results['failed'] += 1
                        continue
                    
                    # Берем первый результат
                    article_result = search_results[0]
                    
                    # Парсим страницу статьи
                    article = self.parser_engine.parse_article_page(article_result['url'])
                    
                    if article:
                        # Сохраняем статью
                        saved_path = self.article_manager.save_article(article)
                        
                        if saved_path:
                            results['success'] += 1
                            results['articles'].append({
                                'title': article.title,
                                'url': article.url,
                                'word_count': article.word_count,
                                'file_path': saved_path
                            })
                        else:
                            results['failed'] += 1
                    else:
                        results['failed'] += 1
                    
                    # Задержка между запросами
                    time.sleep(config.REQUEST_DELAY)
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка при обработке статьи '{article_title}': {e}")
                    results['failed'] += 1
                    continue
            
            # Экспортируем результаты
            self.export_results()
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка парсинга: {e}")
        finally:
            # Закрываем ресурсы
            self.parser_engine.close()
            
            # Считаем общее время
            results['total_time'] = time.time() - start_time
            
            # Логируем результаты
            self.log_results(results)
        
        return results
    
    async def async_parse_articles(self, articles_list: List[str]) -> Dict:
        """Асинхронный парсинг статей (экспериментальный)"""
        self.logger.info("⚡ Запуск асинхронного парсинга")
        
        # Этот метод можно доработать для асинхронного парсинга
        # Пока используем синхронную версию
        return self.parse_articles_batch(articles_list)
    
    def smart_search(self, query: str, use_semantic: bool = False) -> List[Dict]:
        """Умный поиск статей с различными стратегиями"""
        self.logger.info(f"🔍 Умный поиск: {query}")
        
        try:
            self.parser_engine.init_selenium()
            
            if not self.parser_engine.smart_login():
                return []
            
            # Стратегия 1: Прямой поиск
            results = self.parser_engine.search_articles(query)
            
            # Стратегия 2: Расширенный поиск по синонимам
            if not results and use_semantic:
                results = self.expanded_search(query)
            
            # Стратегия 3: Поиск по связанным темам
            if not results:
                results = self.related_topics_search(query)
            
            self.parser_engine.close()
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка умного поиска: {e}")
            return []
    
    def expanded_search(self, query: str) -> List[Dict]:
        """Расширенный поиск с синонимами"""
        # База синонимов (можно расширить)
        synonyms = {
            'электроэнергия': ['электричество', 'электроснабжение', 'энергия'],
            'долг': ['задолженность', 'задолж', 'неоплата'],
            'тариф': ['расценка', 'ставка', 'цена'],
            'счетчик': ['прибор учета', 'ПУ', 'измеритель'],
            'льгота': ['преференция', 'скидка', 'субсидия']
        }
        
        search_queries = [query]
        
        # Добавляем синонимы
        for word in query.split():
            if word.lower() in synonyms:
                for synonym in synonyms[word.lower()]:
                    new_query = query.replace(word, synonym)
                    search_queries.append(new_query)
        
        # Выполняем поиск по всем вариантам
        all_results = []
        for search_query in search_queries[:3]:  # Ограничиваем количество запросов
            results = self.parser_engine.search_articles(search_query)
            all_results.extend(results)
        
        # Удаляем дубликаты
        unique_results = []
        seen_urls = set()
        
        for result in all_results:
            if result['url'] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result['url'])
        
        return unique_results
    
    def related_topics_search(self, query: str) -> List[Dict]:
        """Поиск по связанным темам"""
        related_keywords = self.generate_related_keywords(query)
        all_results = []
        
        for keyword in related_keywords[:2]:  # Ограничиваем количество
            results = self.parser_engine.search_articles(keyword)
            all_results.extend(results)
        
        # Удаляем дубликаты
        unique_results = []
        seen_urls = set()
        
        for result in all_results:
            if result['url'] not in seen_urls:
                unique_results.append(result)
                seen_urls.add(result['url'])
        
        return unique_results
    
    def generate_related_keywords(self, query: str) -> List[str]:
        """Генерация связанных ключевых слов"""
        # Простая логика генерации связанных тем
        # Можно заменить на ML модель или более сложную логику
        topic_map = {
            'электроэнергия': ['оплата электроэнергии', 'тарифы на электричество', 'потребление энергии'],
            'долг': ['погашение задолженности', 'рассрочка платежа', 'отключение за долги'],
            'тариф': ['изменение тарифа', 'многотарифный учет', 'тарифное расписание'],
            'счетчик': ['замена счетчика', 'показания счетчика', 'поверка прибора учета'],
            'льгота': ['оформление льготы', 'льготы ветеранам', 'социальные льготы']
        }
        
        related = []
        for word in query.split():
            if word.lower() in topic_map:
                related.extend(topic_map[word.lower()])
        
        return related if related else [query]
    
    def export_results(self):
        """Экспорт всех результатов"""
        self.logger.info("📤 Экспорт результатов...")
        
        # Экспорт в CSV
        csv_path = self.article_manager.export_to_csv()
        if csv_path:
            self.logger.info(f"✅ CSV экспорт: {csv_path}")
        
        # Экспорт в Excel
        excel_path = self.article_manager.export_to_excel()
        if excel_path:
            self.logger.info(f"✅ Excel экспорт: {excel_path}")
    
    def log_results(self, results: Dict):
        """Логирование результатов парсинга"""
        self.logger.info("\n" + "="*50)
        self.logger.info("📊 РЕЗУЛЬТАТЫ ПАРСИНГА")
        self.logger.info("="*50)
        self.logger.info(f"✅ Успешно: {results['success']}")
        self.logger.info(f"❌ Ошибки: {results['failed']}")
        self.logger.info(f"⏭️ Пропущено: {results.get('skipped', 0)}")
        self.logger.info(f"⏱️ Общее время: {results['total_time']:.2f} сек")
        self.logger.info(f"📈 Эффективность: {(results['success'] / (results['success'] + results['failed']) * 100):.1f}%")
        self.logger.info("="*50)
        
        # Сохраняем результаты в файл
        try:
            results_file = f"{config.LOGS_DIR}/parsing_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 Результаты сохранены: {results_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения результатов: {e}")
    
    def get_detailed_stats(self) -> Dict:
        """Получение детальной статистики"""
        basic_stats = self.article_manager.get_stats()
        parsing_stats = self.get_parsing_stats()
        
        return {
            **basic_stats,
            **parsing_stats,
            'parser_version': '2.0.0',
            'last_run': time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_parsing_stats(self) -> Dict:
        """Статистика парсинга"""
        return {
            'articles_found': self.parser_engine.articles_found,
            'articles_parsed': self.parser_engine.articles_parsed,
            'success_rate': (self.parser_engine.articles_parsed / self.parser_engine.articles_found * 100) 
                            if self.parser_engine.articles_found > 0 else 0
        }
    
    def close(self):
        """Закрытие всех ресурсов"""
        self.parser_engine.close()
        self.executor.shutdown()
