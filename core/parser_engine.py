import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent
import json
import time
import logging
from urllib.parse import urljoin, urlparse
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
import re

@dataclass
class Article:
    title: str
    url: str
    content: str
    category: str = ""
    tags: List[str] = None
    metadata: Dict = None
    word_count: int = 0
    timestamp: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.word_count = len(self.content.split())

class ParserEngine:
    def __init__(self, config):
        self.config = config
        self.ua = UserAgent()
        self.session = None
        self.driver = None
        self.articles_found = 0
        self.articles_parsed = 0
        self.setup_logging()
        
    def setup_logging(self):
        """Настройка логирования"""
        os.makedirs(self.config.LOGS_DIR, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{self.config.LOGS_DIR}/parser.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_selenium(self):
        """Инициализация Selenium с продвинутыми настройками"""
        chrome_options = Options()
        
        if self.config.HEADLESS:
            chrome_options.add_argument("--headless=new")
        
        # Скрываем автоматизацию
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Рандомный User-Agent
        chrome_options.add_argument(f"--user-agent={self.ua.random}")
        
        # Дополнительные настройки для обхода защиты
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Скрываем WebDriver
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.ua.random
        })
        
        self.logger.info("✅ Selenium инициализирован")
    
    async def init_async_session(self):
        """Инициализация асинхронной сессии"""
        timeout = aiohttp.ClientTimeout(total=self.config.TIMEOUT)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={'User-Agent': self.ua.random}
        )
    
    def smart_login(self):
        """Умная авторизация с различными стратегиями"""
        self.logger.info("🔐 Попытка умной авторизации...")
        
        try:
            self.driver.get(self.config.BASE_URL)
            time.sleep(2)
            
            # Стратегия 1: Проверяем, уже авторизованы ли мы
            if self.is_authenticated():
                self.logger.info("✅ Уже авторизован")
                return True
            
            # Стратегия 2: Пробуем найти и заполнить форму логина
            if self.config.USERNAME and self.config.PASSWORD:
                if self.fill_login_form():
                    self.logger.info("✅ Авторизация через форму успешна")
                    return True
            
            # Стратегия 3: Ожидаем ручной авторизации
            self.logger.info("🔄 Ожидаем ручной авторизации...")
            input("🔑 Пожалуйста, авторизуйтесь в браузере и нажмите Enter...")
            
            return self.is_authenticated()
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка авторизации: {e}")
            return False
    
    def is_authenticated(self):
        """Проверка статуса авторизации"""
        try:
            # Ищем индикаторы авторизации
            auth_indicators = [
                '[href*="logout"]',
                '.user-menu',
                '.user-info',
                '.logout',
                '[class*="user"]',
                '[class*="profile"]'
            ]
            
            for indicator in auth_indicators:
                elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                if elements:
                    return True
            
            # Проверяем URL
            current_url = self.driver.current_url
            if "login" not in current_url and "auth" not in current_url:
                return True
                
            return False
            
        except:
            return False
    
    def fill_login_form(self):
        """Заполнение формы логина"""
        try:
            selectors = self.config.SELECTORS
            
            # Ищем форму логина
            form_selectors = [selectors['login_form'], 'form', 'form[method="post"]']
            
            for form_selector in form_selectors:
                try:
                    forms = self.driver.find_elements(By.CSS_SELECTOR, form_selector)
                    for form in forms:
                        # Пробуем найти поля ввода
                        username_fields = form.find_elements(By.CSS_SELECTOR, selectors['username_field'])
                        password_fields = form.find_elements(By.CSS_SELECTOR, selectors['password_field'])
                        submit_buttons = form.find_elements(By.CSS_SELECTOR, selectors['submit_button'])
                        
                        if username_fields and password_fields and submit_buttons:
                            username_fields[0].send_keys(self.config.USERNAME)
                            password_fields[0].send_keys(self.config.PASSWORD)
                            submit_buttons[0].click()
                            time.sleep(3)
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка заполнения формы: {e}")
            return False
    
    def search_articles(self, query: str) -> List[Dict]:
        """Поиск статей по запросу"""
        self.logger.info(f"🔍 Поиск статей: {query}")
        
        try:
            # Стратегия 1: Используем поиск на сайте
            search_url = f"{self.config.BASE_URL}/search?q={requests.utils.quote(query)}"
            self.driver.get(search_url)
            time.sleep(2)
            
            # Ищем результаты
            articles = self.extract_search_results()
            
            # Стратегия 2: Если нет результатов, пробуем другой подход
            if not articles:
                articles = self.alternative_search(query)
            
            self.logger.info(f"✅ Найдено {len(articles)} результатов для '{query}'")
            return articles
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска: {e}")
            return []
    
    def extract_search_results(self) -> List[Dict]:
        """Извлечение результатов поиска"""
        articles = []
        
        try:
            # Различные селекторы для результатов поиска
            result_selectors = [
                self.config.SELECTORS['article_links'],
                '.search-result',
                '.result-item',
                '[class*="result"]',
                '.article-item',
                '.content-item'
            ]
            
            for selector in result_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            title = element.text.strip()
                            url = element.get_attribute('href')
                            
                            if title and url and '/content/' in url:
                                articles.append({
                                    'title': title,
                                    'url': url,
                                    'element': element
                                })
                        except:
                            continue
                    
                    if articles:
                        break
                except:
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения результатов: {e}")
            return []
    
    def alternative_search(self, query: str) -> List[Dict]:
        """Альтернативные методы поиска"""
        articles = []
        
        try:
            # Стратегия: Получаем все ссылки на странице и фильтруем по ключевым словам
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    if href and '/content/' in href:
                        # Проверяем релевантность по заголовку
                        if (query.lower() in text.lower() or 
                            any(word in text.lower() for word in query.lower().split())):
                            
                            articles.append({
                                'title': text,
                                'url': href,
                                'element': link
                            })
                except:
                    continue
            
            return articles
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка альтернативного поиска: {e}")
            return []
    
    def parse_article_page(self, url: str) -> Optional[Article]:
        """Парсинг страницы статьи"""
        self.logger.info(f"📖 Парсинг статьи: {url}")
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                self.driver.get(url)
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Извлекаем заголовок
                title = self.extract_title()
                
                # Извлекаем контент
                content = self.extract_content()
                
                # Извлекаем метаданные
                metadata = self.extract_metadata()
                
                # Создаем объект статьи
                article = Article(
                    title=title,
                    url=url,
                    content=content,
                    metadata=metadata
                )
                
                self.articles_parsed += 1
                self.logger.info(f"✅ Успешно спарсена: {title}")
                return article
                
            except Exception as e:
                self.logger.warning(f"⚠️ Попытка {attempt + 1} не удалась: {e}")
                time.sleep(2)
        
        self.logger.error(f"❌ Не удалось спарсить статью: {url}")
        return None
    
    def extract_title(self) -> str:
        """Извлечение заголовка статьи"""
        title_selectors = [
            self.config.SELECTORS['article_title'],
            'h1',
            'h2',
            '.title',
            '.header',
            '.page-title',
            '[class*="title"]',
            '[class*="header"]'
        ]
        
        for selector in title_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    title = element.text.strip()
                    if title and len(title) > 5:
                        return title
            except:
                continue
        
        return "Заголовок не найден"
    
    def extract_content(self) -> str:
        """Извлечение контента статьи"""
        content_parts = []
        
        # Основные селекторы контента
        content_selectors = [
            self.config.SELECTORS['article_content'],
            'article',
            '.content',
            '.post-content',
            '.main-content',
            '.body-content',
            '.text-content',
            '[class*="content"]',
            '[class*="article"]',
            '[class*="post"]'
        ]
        
        for selector in content_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > 100:  # Минимальная длина
                        content_parts.append(text)
            except:
                continue
        
        # Если не нашли структурированный контент, берем основной текст
        if not content_parts:
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                content_parts.append(body.text)
            except:
                pass
        
        # Очищаем и объединяем контент
        clean_content = self.clean_content("\n\n".join(content_parts))
        return clean_content if clean_content else "Контент не найден"
    
    def clean_content(self, text: str) -> str:
        """Очистка контента от мусора"""
        if not text:
            return ""
        
        # Удаляем лишние пробелы и переносы
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Удаляем JavaScript и CSS
        text = re.sub(r'<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>', '', text)
        text = re.sub(r'<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>', '', text)
        
        # Удаляем HTML теги
        text = re.sub(r'<[^>]+>', '', text)
        
        # Удаляем специальные символы (оставляем только текст)
        text = re.sub(r'[^\w\sа-яА-ЯёЁ.,!?;:()\-–—]', '', text)
        
        return text.strip()
    
    def extract_metadata(self) -> Dict:
        """Извлечение метаданных статьи"""
        metadata = {}
        
        try:
            # Дата публикации
            date_selectors = ['.date', '.published', '.created', '[class*="date"]']
            for selector in date_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        metadata['date'] = elements[0].text.strip()
                        break
                except:
                    continue
            
            # Автор
            author_selectors = ['.author', '.byline', '[class*="author"]']
            for selector in author_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        metadata['author'] = elements[0].text.strip()
                        break
                except:
                    continue
            
            # Категория/теги
            category_selectors = ['.category', '.tags', '.topic', '[class*="category"]']
            for selector in category_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        metadata['category'] = elements[0].text.strip()
                        break
                except:
                    continue
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка извлечения метаданных: {e}")
        
        return metadata
    
    def close(self):
        """Закрытие ресурсов"""
        try:
            if self.driver:
                self.driver.quit()
                self.logger.info("🔚 Браузер закрыт")
            
            if self.session:
                asyncio.run(self.session.close())
        except Exception as e:
            self.logger.error(f"❌ Ошибка при закрытии: {e}")
