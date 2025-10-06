import json
import pandas as pd
import os
import hashlib
from datetime import datetime
from typing import List, Dict
import logging
from .parser_engine import Article

class ArticleManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.articles_file = os.path.join(data_dir, "articles.json")
        self.stats_file = os.path.join(data_dir, "stats.json")
        self.setup_directories()
        self.logger = logging.getLogger(__name__)
    
    def setup_directories(self):
        """Создание необходимых директорий"""
        os.makedirs(self.data_dir, exist_ok=True)
    
    def generate_article_id(self, article: Article) -> str:
        """Генерация уникального ID для статьи"""
        content_hash = hashlib.md5(article.content.encode()).hexdigest()[:10]
        title_slug = "".join(c for c in article.title if c.isalnum())[:20]
        return f"{title_slug}_{content_hash}"
    
    def save_article(self, article: Article) -> str:
        """Сохранение статьи в JSON"""
        try:
            article_id = self.generate_article_id(article)
            
            article_data = {
                'id': article_id,
                'title': article.title,
                'url': article.url,
                'content': article.content,
                'category': article.category,
                'tags': article.tags,
                'metadata': article.metadata,
                'word_count': article.word_count,
                'timestamp': article.timestamp,
                'parsed_at': datetime.now().isoformat()
            }
            
            # Сохраняем отдельным файлом
            filename = f"{article_id}.json"
            filepath = os.path.join(self.data_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
            
            # Обновляем общий индекс
            self.update_articles_index(article_data)
            
            self.logger.info(f"💾 Статья сохранена: {filename}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения статьи: {e}")
            return ""
    
    def update_articles_index(self, article_data: Dict):
        """Обновление общего индекса статей"""
        try:
            index_file = os.path.join(self.data_dir, "articles_index.json")
            
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)
            else:
                index = []
            
            # Добавляем только основные данные для индекса
            index_entry = {
                'id': article_data['id'],
                'title': article_data['title'],
                'url': article_data['url'],
                'category': article_data['category'],
                'word_count': article_data['word_count'],
                'timestamp': article_data['timestamp']
            }
            
            # Удаляем дубликаты
            index = [item for item in index if item['id'] != index_entry['id']]
            index.append(index_entry)
            
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(index, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления индекса: {e}")
    
    def export_to_csv(self) -> str:
        """Экспорт всех статей в CSV"""
        try:
            index_file = os.path.join(self.data_dir, "articles_index.json")
            
            if not os.path.exists(index_file):
                self.logger.warning("⚠️ Нет данных для экспорта")
                return ""
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            df = pd.DataFrame(index)
            csv_path = os.path.join(self.data_dir, "articles_export.csv")
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"📊 CSV экспорт создан: {csv_path}")
            return csv_path
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка экспорта в CSV: {e}")
            return ""
    
    def export_to_excel(self) -> str:
        """Экспорт в Excel с дополнительной информацией"""
        try:
            articles_data = []
            
            # Собираем данные из всех файлов статей
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json') and filename != 'articles_index.json':
                    filepath = os.path.join(self.data_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        article = json.load(f)
                        articles_data.append(article)
            
            if not articles_data:
                self.logger.warning("⚠️ Нет данных для экспорта в Excel")
                return ""
            
            df = pd.DataFrame(articles_data)
            excel_path = os.path.join(self.data_dir, "articles_export.xlsx")
            
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Статьи', index=False)
                
                # Создаем лист со статистикой
                stats_data = {
                    'Метрика': ['Всего статей', 'Общее количество слов', 'Дата экспорта'],
                    'Значение': [len(articles_data), df['word_count'].sum(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Статистика', index=False)
            
            self.logger.info(f"📊 Excel экспорт создан: {excel_path}")
            return excel_path
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка экспорта в Excel: {e}")
            return ""
    
    def search_articles(self, query: str) -> List[Dict]:
        """Поиск статей по запросу"""
        try:
            results = []
            query = query.lower()
            
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json') and filename != 'articles_index.json':
                    filepath = os.path.join(self.data_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        article = json.load(f)
                        
                        # Поиск по заголовку и контенту
                        if (query in article['title'].lower() or 
                            query in article['content'].lower() or
                            any(query in tag.lower() for tag in article.get('tags', []))):
                            
                            results.append({
                                'id': article['id'],
                                'title': article['title'],
                                'url': article['url'],
                                'excerpt': article['content'][:200] + '...',
                                'word_count': article['word_count'],
                                'timestamp': article['timestamp']
                            })
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Получение статистики"""
        try:
            index_file = os.path.join(self.data_dir, "articles_index.json")
            
            if not os.path.exists(index_file):
                return {'total_articles': 0, 'total_words': 0}
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
            
            total_words = sum(article.get('word_count', 0) for article in index)
            
            return {
                'total_articles': len(index),
                'total_words': total_words,
                'last_update': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статистики: {e}")
            return {'total_articles': 0, 'total_words': 0}
