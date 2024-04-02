import aiohttp_jinja2
import jinja2
from aiohttp import web
import configparser
import aiomysql
import asyncio
import json

class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr

class Config:
    """负责读取和管理配置文件的类。
    主要用于从config.ini配置文件中加载数据库连接信息、服务器端口以及其他配置项。
    """
    def __init__(self, filename='config.ini'):
        self.config = CaseSensitiveConfigParser()
        self.config.read(filename)

    def db_config(self):
        config = self.config['database']
        return {
            'host': config.get('host'),
            'port': int(config.get('port', 3306)),
            'user': config.get('user'),
            'password': config.get('password'),
            'db': config.get('database'), 
            'charset': 'utf8mb4',
        }

    def server_port(self):
        return int(self.config['server'].get('port', 80))
    
    def articles_table(self):
        return self.config['settings'].get('arxiv_table')
    
    def categories(self):
        return [category.strip() for category in self.config['settings'].get('categories').split(',')]

async def create_db_pool(loop, **db_config):
    """Creates and returns an aiomysql connection pool."""
    db_config['pool_recycle'] = 3600
    db_config['autocommit'] = True # To update connection between server and database
    return await aiomysql.create_pool(loop=loop, **db_config)

async def get_latest_article_date_and_count(pool, table_name):
    """Fetches the latest article date and count from the specified table."""
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(f"SELECT MAX(DATE(updated)) as latest_date FROM {table_name}")
            result = await cur.fetchone()
            latest_date = result['latest_date'] if result else 'N/A'
            
            await cur.execute(f"SELECT COUNT(*) as count FROM {table_name} WHERE DATE(updated) = %s", (latest_date,))
            count_result = await cur.fetchone()
            count = count_result['count'] if count_result else 0
    return latest_date, count
        
async def fetch_articles(pool, table_name):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 查询最新更新日期
            await cur.execute(f"SELECT MAX(updated) FROM {table_name}")
            result = await cur.fetchone()
            latest_date = result['MAX(updated)'] if result else None

            articles_data = []
            if latest_date:
                # 根据最新更新日期查询文章信息
                await cur.execute("""
                    SELECT title, summary, authors, categories, comment, entry_id, 
                           journal_ref, updated, CN_title, CN_summary
                    FROM {}
                    WHERE DATE(updated) = DATE(%s)
                    ORDER BY updated DESC
                """.format(table_name), (latest_date,))  # 注意SQL注入风险
                articles_data = await cur.fetchall()
            return articles_data
        
async def index(request):
    """Handles the index route."""
    pool = request.app['db_pool']
    config = request.app['config']
    categories = config.categories()
    latest_update, count = await get_latest_article_date_and_count(pool, config.articles_table())
    return aiohttp_jinja2.render_template('index.html', request, {'title': 'Arxiv Day', 'categories': categories, 'latest_update': latest_update, 'count': count})

async def handle_404(request):
    return aiohttp_jinja2.render_template('404.html', request, {}, status=404)

async def artilce_handler(request):
    path = request.match_info.get('path', "")
    pool = request.app['db_pool']
    config = request.app['config']
    selected_date = request.query.get('date')

    table_name = config.articles_table()
    categories = json.dumps(config.categories())

    if selected_date:
        articles = await fetch_articles_by_date(pool, table_name, selected_date)
    else:
        articles = await fetch_articles(pool, table_name)
    
    # 这里假设articles是一个包含所有文章信息的列表
    return aiohttp_jinja2.render_template('article.html', request, {
        'title': 'Arxiv: ' + path.upper(), 
        'categories': categories,
        'articles': articles, 'path': path})

async def fetch_articles_by_date(pool, table_name, date):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(f"""
                SELECT title, summary, authors, categories, comment, entry_id, 
                       journal_ref, updated, CN_title, CN_summary
                FROM {table_name}
                WHERE DATE(updated) = %s
                ORDER BY updated DESC
            """, (date,))
            articles_data = await cur.fetchall()
    return articles_data

async def fetch_years_with_articles(pool, table_name):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(f"SELECT DISTINCT YEAR(updated) AS year FROM {table_name} ORDER BY year DESC")
            years_data = await cur.fetchall()
    return [entry['year'] for entry in years_data if entry['year']]

async def fetch_days_with_articles(pool, table_name):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(f"""
                SELECT DISTINCT DATE(updated) AS day
                FROM {table_name}
                ORDER BY day DESC
            """)
            days_data = await cur.fetchall()
    # 将日期对象转换为字符串
    return [entry['day'].strftime('%Y-%m-%d') for entry in days_data if entry['day']]


async def calendar_handler(request):
    pool = request.app['db_pool']
    config = request.app['config']
    categories = config.categories()
    table_name = config.articles_table()
    days_with_articles = await fetch_days_with_articles(pool, table_name)
    years_with_articles = await fetch_years_with_articles(pool, table_name)

    return aiohttp_jinja2.render_template('calendar.html', request, {
        'title': 'Arxiv Day: Calendar',
        'categories': categories,
        'years_with_articles': years_with_articles,
        'days_with_articles': days_with_articles
    })



async def init_app():
    """Initializes and returns the web application."""
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    config = Config('config.ini')
    loop = asyncio.get_running_loop()
    db_pool = await create_db_pool(loop, **config.db_config())
    app['db_pool'] = db_pool
    app['config'] = config

    # index页面
    app.router.add_get('/', index)

    # articles页面
    app.router.add_route('GET', '/articles', artilce_handler)

    # calendar页面
    app.router.add_get('/calendar', calendar_handler)

    # 404页面渲染
    app.router.add_get('/{tail:.*}', handle_404)

    return app

if __name__ == "__main__":
    port = Config('config.ini').server_port()
    app = init_app()
    web.run_app(app, port=port)