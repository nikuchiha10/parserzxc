import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7220498387:AAEPlB9BLtTdmzUtRoD2pXhsoB3UzsnoMzE")
    ADMIN_IDS = [6910167987]
    
    # Parser
    BASE_URL = "https://mes1-kms.interrao.ru"
    LOGIN_URL = f"{BASE_URL}/login"
    CONTENT_SPACE_URL = f"{BASE_URL}/content/space/4"
    
    # Auth (если нужно)
    USERNAME = os.getenv("KMS_USERNAME", "")
    PASSWORD = os.getenv("KMS_PASSWORD", "")
    
    # Browser
    HEADLESS = True
    TIMEOUT = 30
    MAX_RETRIES = 3
    REQUEST_DELAY = 1
    
    # Selectors (адаптируйте под целевой сайт)
    SELECTORS = {
        'login_form': 'form[action*="login"]',
        'username_field': 'input[name="username"], input[type="email"]',
        'password_field': 'input[name="password"], input[type="password"]',
        'submit_button': 'button[type="submit"], input[type="submit"]',
        'search_input': 'input[type="search"], input[name="search"]',
        'article_links': 'a[href*="/content/"], .article-link, .content-item a',
        'article_title': 'h1, .article-title, .page-title',
        'article_content': 'article, .article-content, .content, .post-content',
        'pagination': '.pagination, .page-links, [class*="pagination"]'
    }
    
    # Files
    DATA_DIR = "data"
    LOGS_DIR = "logs"
    BACKUP_DIR = "backups"
    
    # Performance
    MAX_CONCURRENT_REQUESTS = 5
    MAX_ARTICLES_PER_RUN = 50

config = Config()
