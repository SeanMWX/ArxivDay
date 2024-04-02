import aiohttp_jinja2
import jinja2
from aiohttp import web
import configparser
import aiomysql
import asyncio

class Config:
    """负责读取和管理配置文件的类。
    主要用于从config.ini配置文件中加载数据库连接信息、服务器端口以及其他配置项。
    """
    def __init__(self, filename='config.ini'):
        self.config = configparser.ConfigParser()
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
    
    def categories_and_tables(self):
        return self.config['categories_and_tables']

async def create_db_pool(loop, **db_config):
    db_config['pool_recycle'] = 3600
    db_config['autocommit'] = True # To update connection between server and database
    """Creates and returns an aiomysql connection pool."""
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

async def fetch_articles_from_table(pool, table_name):
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
    categories_and_tables = request.app['config'].categories_and_tables()
    categories_info = {}
    for category, table_name in categories_and_tables.items():
        latest_update, count = await get_latest_article_date_and_count(pool, table_name)
        categories_info[category] = {
            'name': category.upper(),
            'latest_update': latest_update,
            'count': count
        }
    return aiohttp_jinja2.render_template('index.html', request, {'title': 'Arxiv Day', 'categories_info': categories_info})

async def handle_404(request):
    return aiohttp_jinja2.render_template('404.html', request, {}, status=404)

async def artilce_handler(request):
    path = request.match_info.get('path', "")
    pool = request.app['db_pool']
    config = request.app['config']

    if path not in config.categories_and_tables():
        # 如果找不到路径对应的表，返回404页面
        return aiohttp_jinja2.render_template('404.html', request, {}, status=404)

    table_name = config.categories_and_tables()[path]
    articles = await fetch_articles_from_table(pool, table_name)
    
    # 这里假设articles是一个包含所有文章信息的列表
    return aiohttp_jinja2.render_template('article.html', request, {
        'title': 'Arxiv: ' + path.upper(), 
        'articles_count': len(articles), 
        'last_updated': articles[0]['updated'].strftime('%Y-%m-%d %H:%M:%S') if articles else 'N/A',
        'articles': articles, 'path': path})


async def init_app():
    """Initializes and returns the web application."""
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates'))
    config = Config('config.ini')
    loop = asyncio.get_running_loop()
    db_pool = await create_db_pool(loop, **config.db_config())
    app['db_pool'] = db_pool
    app['config'] = config

    app.router.add_get('/', index)

    # cs.AI, cs.CR页面
    app.router.add_route('GET', '/{path}', artilce_handler)

    # 404页面渲染
    app.router.add_get('/{tail:.*}', handle_404)

    return app

if __name__ == "__main__":
    port = Config('config.ini').server_port()
    app = init_app()
    web.run_app(app, port=port)