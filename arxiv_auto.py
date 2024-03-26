from datetime import datetime, timedelta
from openai import OpenAI
import arxiv
import configparser
import mysql.connector
from mysql.connector import Error
import schedule
import time

class Article:
    """
    表示从arXiv获取的文章的类，包含文章的各种元数据以及翻译方法。
    """
    def __init__(self, authors=None, categories=None, comment=None, doi=None, entry_id=None, 
                 journal_ref=None, links=None, primary_category=None, published=None, summary=None, 
                 title=None, updated=None, CN_title=None, CN_summary=None):
            
        self.authors = [author.name or '' for author in authors] if authors is not None else []
        self.categories = categories or ""
        self.comment = comment or ""
        self.doi = doi or ""
        self.entry_id = entry_id or ""
        
        self.journal_ref = journal_ref or ""
        self.links = [f"{link.href or ''},{link.title or ''},{link.rel or ''},{link.content_type or ''}" for link in links] if links is not None else []
        self.primary_category = primary_category or ""
        self.published = published or ""
        self.summary = summary or ""
        self.title = title or ""
        self.updated = updated or ""

    def gpt_CN_translate(self, model):
        print("Running ChatGPT...")
        
        max_retries = 3  # 设置最大重试次数
        retries = 0

        # 翻译标题
        while retries < max_retries:
            try:
                self.CN_title = model.prompt('请帮我翻译这个文献标题：%s' % (self.title))
                break
            except Exception as e:
                retries += 1
                print(f"An error occurred: {e}, Retrying... ({retries}/{max_retries})")

        # 检查是否超出重试次数
        if retries == max_retries:
            print("Failed to translate {self.title} after maximum retries.")
            self.CN_title = "Translation failed."

        # 重置重试次数
        retries = 0

        while retries < max_retries:
            try:
                self.CN_summary = model.prompt('请帮我翻译这个文献摘要：%s' % (self.summary))
                break
            except Exception as e:
                retries += 1
                print(f"An error occurred: {e}, Retrying... ({retries}/{max_retries})")

        # 检查是否超出重试次数
        if retries == max_retries:
            print("Failed to translate <summary> after maximum retries.")
            self.CN_summary = "Translation failed."
            
        print("Job done.")

class ChatGPTModel:
    """
    封装与ChatGPT模型交互的方法，主要用于将英文标题和摘要翻译成中文。
    """
    # GPT API pricing: https://openai.com/pricing
    def __init__(self, api_key=None, model="gpt-3.5-turbo-0125"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def prompt(self, message, temperature=0.7, max_tokens=2000):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": message,
                    }
                ],
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"An error occurred: {e}")

class Config:
    """
    管理配置文件（config.ini）的类，用于读取数据库配置和API密钥。
    """
    def __init__(self, filename='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(filename)

    def db_config(self):
        return self.config['database']

    def api_key(self):
        return self.config['chatgpt']['api_key']
    
    def categories_and_tables(self):
        return {f"cat:{k}": v for k, v in self.config['categories_and_tables'].items()}
    
    def fetch_frequency(self):
        return int(self.config['schedule']['frequency_hours'])
    
    def max_results(self):
        return int(self.config.get('settings', 'max_results', fallback='500'))
    
class Database:
    """
    数据库操作类，用于管理与MySQL数据库的连接和操作。
    包括检查文章是否已存在于数据库中以及插入新文章。
    """
    def __init__(self, db_config):
        self.db_config = db_config

    def get_connection(self):
        return mysql.connector.connect(**self.db_config)
    
    def article_exists(self, entry_id, table_name):
        config = Config()
        table_names = config.categories_and_tables().values()
        query = f"SELECT COUNT(1) FROM {table_name} WHERE entry_id = %s"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (entry_id,))
            result = cursor.fetchone()
            return result[0] > 0

def fetch_recent_articles(category, max_results=500):
    """
    获取最近更新的文章列表。通过arXiv API获取指定分类下最新的文章列表。
    """
    client = arxiv.Client()
    search = arxiv.Search(
        query=category,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.LastUpdatedDate
    )

    articles_list = []
    for r in client.results(search):
        article = Article(
            r.authors, r.categories, r.comment, r.doi,
            r.entry_id, r.journal_ref, r.links,
            r.primary_category, r.published, r.summary, r.title, r.updated
        )
        articles_list.append(article)

    return articles_list

def translate_articles(articles):
    """
    使用ChatGPT模型翻译文章标题和摘要。将获取的文章列表中的每篇文章标题和摘要送至ChatGPT进行中文翻译。
    """
    config = Config()
    model = ChatGPTModel(api_key=config.api_key())
    for article in articles:
        article.gpt_CN_translate(model)

def fetch_process_insert_articles(category, table_name, max_results):
    """
    处理文章列表：翻译和插入数据库，避免重复。集成了文章获取、翻译和插入数据库的全过程，只对数据库中不存在的新文章进行处理。
    """
    config = Config()
    model = ChatGPTModel(api_key=config.api_key())
    db = Database(config.db_config())

    print(f"（{datetime.now().date()}）：开始检索{category}文章...")
    articles = fetch_recent_articles(category, max_results)

    insert_articles = []
    if articles:
        for article in articles:
            if not db.article_exists(article.entry_id, table_name):
                insert_articles.append(article)
    else:
        print(f"（{datetime.now().date()}）：没有获取到任何{category}文章。")
    
    if insert_articles:
        print(f"更新{category}文章数目为{len(insert_articles)}篇。")
        num = 0
        for article in insert_articles:
            print(f"Job. {num+1}/{len(insert_articles)}:") 
            article.gpt_CN_translate(model)
            num += 1
        insert_articles_to_database(insert_articles, table_name)  # 插入新文章到数据库
        print(f"成功更新{num}篇。")
    else:
        print("没有新的文章需要更新。")

def insert_articles_to_database(articles, table_name):
    """
    将文章数据插入数据库。负责将处理过的文章数据批量插入数据库中。
    """
    insert_query = f"""
    INSERT INTO {table_name} 
    (title, summary, published, authors, categories, comment, doi, entry_id, journal_ref, links, primary_category, updated, CN_title, CN_summary) 
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    records = [(article.title, article.summary, article.published, 
                ",".join(article.authors), ",".join(article.categories), article.comment, 
                article.doi, article.entry_id, article.journal_ref, 
                ",".join(article.links), article.primary_category, article.updated, 
                article.CN_title, article.CN_summary) for article in articles]

    config = Config()
    db = Database(config.db_config())

    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.executemany(insert_query, records)
        conn.commit()
        print(f"{cursor.rowcount} records inserted.")
    except Error as e:
        print(e)
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def daily_task():
    """
    定义定时任务要执行的操作。对配置文件中指定的每个文章分类，调用`fetch_process_insert_articles`函数进行文章的抓取、处理和插入操作。
    """
    config = Config()
    for category, table_name in config.categories_and_tables().items():
        fetch_process_insert_articles(category, table_name, config.max_results())

# 主程序流程
if __name__ == "__main__":
    config = Config()
    frequency_hours = config.fetch_frequency()  # 获取收录频率
    print(f"当前本地时间: {datetime.now()}")
    daily_task()
    schedule.every(frequency_hours).hours.do(daily_task)

    while True:
        # 获取当前UTC时间
        print(f"当前本地时间: {datetime.now()}")
        # 运行所有可以运行的任务
        schedule.run_pending()
        time.sleep(60)  # 暂停一分钟