import configparser
from http.server import BaseHTTPRequestHandler, HTTPServer
import mysql.connector
from mysql.connector import Error
from urllib.parse import urlparse

class Config:
    """负责读取和管理配置文件的类。
    主要用于从config.ini配置文件中加载数据库连接信息、服务器端口以及其他配置项。
    """
    def __init__(self, filename='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(filename)

    def db_config(self):
        return self.config['database']

    def server_port(self):
        return int(self.config['server'].get('port', 80))
    
    def categories_and_tables(self):
        return self.config['categories_and_tables']

class Database:
    """负责数据库操作的类。
    包括建立数据库连接、从指定表中获取文章数据等。
    """
    def __init__(self, db_config):
        self.db_config = db_config

    def get_connection(self):
        try:
            return mysql.connector.connect(**self.db_config)
        except Error as e:
            print(f"Database connection failed: {e}")
            return None

    def fetch_articles_from_table(self, table_name):
        articles_data = []
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX(updated) FROM {table_name}")
            result = cursor.fetchone()
            latest_date = result[0] if result else None
            
            if latest_date:
                cursor.execute(f"""
                    SELECT title, summary, authors, categories, comment, entry_id, journal_ref, updated, CN_title, CN_summary
                    FROM {table_name}
                    WHERE DATE(updated) = DATE(%s)
                    ORDER BY updated DESC
                """, (latest_date,))
                articles_data = cursor.fetchall()
        return articles_data
    
    def get_latest_article_date_and_count(self, table_name):
        """获取指定表中最新文章的更新日期和当天更新的文章数量"""
        latest_date = None
        count = 0
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 查询最新更新日期
            cursor.execute(f"SELECT MAX(DATE(updated)) FROM {table_name}")
            result = cursor.fetchone()
            if result and result[0]:
                latest_date = result[0]
                
                # 基于最新更新日期，查询当天更新的文章数量
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE DATE(updated) = %s", (latest_date,))
                count_result = cursor.fetchone()
                if count_result:
                    count = count_result[0]
                    
        return latest_date, count



# HTTP请求处理器
class RequestHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器。
    用于处理HTTP GET请求，根据请求的路径返回不同的HTML页面。
    """
    def __init__(self, *args, **kwargs):
        self.config = Config()
        self.db = Database(self.config.db_config())
        self.table_mapping = self.config.categories_and_tables()
        super().__init__(*args, **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path.strip('/')
        if path == "":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_index_html().encode("utf-8"))
            return
        
        if path not in self.table_mapping:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(self.generate_404_html().encode("utf-8"))
            return

        table_name = self.table_mapping[path]
        articles = self.db.fetch_articles_from_table(table_name)
        
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        self.wfile.write(self.generate_html(articles, path).encode("utf-8"))

    def generate_html(self, articles, path):
        html_header = self.generate_html_header(articles, path)
        html_content = self.generate_html_content(articles)
        html_footer = self.generate_html_footer()
        return html_header + html_content + html_footer

    def generate_html_header(self, articles, path):

        # 动态确定页面标题
        page_title = "Arxiv"
        if path:
            # 使用路径来动态确定标题
            page_title += f": {path.upper()}"  # 将路径转换为大写并替换下划线为点，例如 ai -> cs.AI
    

        # Header
        html_header = f"""
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>{page_title}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        """

        html_header += """
        <style>
            /* 基础重置 */
            body, html {
                margin: 0;
                padding: 0;
                height: 100%;
                background-color: #f0f0f2; /* 微妙的灰色背景 */
                color: #333; /* 深灰色文字，增加对比度但不过分强烈 */
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* 更现代的字体 */
            }

            /* 主内容区 */
            .content {
                display: flex;
                justify-content: center;
                text-align: left;
                padding: 20px;
                min-height: calc(100vh - 60px);
                line-height: 1.5;
            }

            /* 内部容器 */
            .inner-content {
                max-width: 1200px;
                width: 100%;
                background: #fff; /* 白色背景提升内容可读性 */
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* 微妙的阴影增加立体感 */
                padding: 20px; /* 内容与边缘的距离 */
                border-radius: 5px; /* 轻微的圆角 */
            }

            /* 页脚样式 */
            .site-info {
                background-color: #f1f1f1; /* 页脚背景色 */
                color: #333; /* 页脚文字色 */
                text-align: center;
                padding: 10px 0;
                font-size: 14px;
            }

            /* 链接样式 */
            a {
                color: #007bff;
                text-decoration: none;
                transition: color 0.3s ease-in-out;
            }

            a:hover, a:focus {
                color: #0056b3;
                text-decoration: underline;
            }

            /* 文章容器样式 */
            .article-container {
                display: flex;
                justify-content: space-between;
                margin-bottom: 20px;
                border-bottom: 1px solid #e0e0e0;
                padding-bottom: 15px;
            }

            /* 文章左侧和右侧样式 */
            .article-left, .article-right {
                width: 48%;
            }

            /* 文章标题和摘要样式 */
            .article-title, .article-summary {
                margin: 5px 0;
            }

            /* 增加科技感的标题样式 */
            h1 {
                color: #333;
                text-align: center;
                font-weight: 300;
                letter-spacing: -1px; /* 字母间距调整 */
            }

            /* 微调滚动条样式 */
            ::-webkit-scrollbar {
                width: 8px;
            }

            ::-webkit-scrollbar-track {
                background: #f1f1f1;
            }

            ::-webkit-scrollbar-thumb {
                background: #888;
            }

            ::-webkit-scrollbar-thumb:hover {
                background: #555;
            }

            .header-info {
                text-align: center;
                padding: 20px;
                background-color: #eef;
                border-bottom: 1px solid #ddd;
            }

            .header-info h1 {
                margin: 0 0 10px 0;
            }

            .header-info p {
                margin: 5px 0;
                color: #666;
                font-size: 16px;
            }
        </style>
    """
        html_header += f"""
    </head>
    <body>
    <div class="header-info">
        <h1>{page_title}</h1>
        <p>Articles: {len(articles)}</p>
        <p>Last Updated: {articles[0][-3].strftime('%Y-%m-%d %H:%M:%S') if articles else 'N/A'} (+00:00)</p>
    </div>
    """
        return html_header

    def generate_html_content(self, articles):
        # 初始化文章内容HTML字符串
        html_content = ""
        html_content = """
    <div class="content">
        <div class="inner-content">        
    """

            # 遍历所有文章，将它们添加到HTML中
        for article in articles:
            title, summary, authors, categories, comment, entry_id, journal_ref, updated, CN_title, CN_summary = article
            html_content += "<div class=\"article-container\">"
            # 英文内容（左侧）
            html_content += f"<div class=\"article-left\"><h3 class=\"article-title\">Title: {title}</h3><p class=\"article-summary\">Summary: {summary}</p><p><i>Updated: {updated}</i></p></div>"
            # 中文内容（右侧）
            html_content += f"""
            <div class=\"article-right\"><h3 class=\"article-title\">标题: {CN_title}</h3><p class=\"article-summary\">摘要: {CN_summary}</p>
            <p><i>更新时间: {updated}</i></p>
            <p><i>领域: {categories}</i></p>
            <p><i>下载: <a href="{entry_id}" target="_blank">{entry_id}</a></i></p>
            </div>
            """
            html_content += "</div>"

        html_content += """
        </div>
    </div>
    """
        return html_content

    def generate_html_footer(self):
        # HTML页面的结尾部分
        html_footer = """
    <div class="site-info">
        Xinhai (Sean) Zou. <br/>
        This website does not contain any JavaScript code. <br/>
    </div>

    </body>
    </html>
    """
        return html_footer
    
    def generate_404_html(self):
        """生成404错误页面的HTML"""
        return f"""
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>404 Not Found</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            background-color: #f0f0f2;
            color: #333;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .content {{
            display: flex;
            justify-content: center;
            text-align: center;
            padding: 20px;
            min-height: calc(100vh - 60px);
            line-height: 1.5;
        }}
        .inner-content {{
            max-width: 1200px;
            width: 100%;
            background: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            border-radius: 5px;
        }}
        .site-info {{
            background-color: #f1f1f1;
            color: #333;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="content">
        <div class="inner-content">
            <h1>404 Not Found</h1>
            <p>The resource you are looking for could not be found.</p>
        </div>
    </div>
    <div class="site-info">
        Xinhai (Sean) Zou. <br/>
        This website does not contain any JavaScript code. <br/>
    </div>
</body>
</html>
        """
    
    def generate_index_html(self):
        # 初始化存储分类信息的字符串
        categories_info = ""

        # 从配置文件中获取所有分类及其对应的数据库表名
        categories_and_tables = self.config.categories_and_tables()

        # 遍历所有分类及其对应的数据库表名
        for category, table_name in categories_and_tables.items():
            # 获取指定表中最新文章的更新日期和当天更新的文章数量
            latest_date, count = self.db.get_latest_article_date_and_count(table_name)
            latest_date_str = latest_date.strftime('%Y-%m-%d') if latest_date else 'N/A'
            
            # 构建并添加当前分类的信息到 categories_info 字符串
            categories_info += f'<p><a href="/{category}">Arxiv: {category.upper()}</a> - Latest Update: {latest_date_str}, Articles: {count}</p>\n'

        return f"""

<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Arxiv Index</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            height: 100%;
            background-color: #f0f0f2;
            color: #333;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        .content {{
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 20px;
            min-height: calc(100vh - 60px);
            line-height: 1.5;
        }}
        .inner-content {{
            max-width: 1200px;
            width: 100%;
            background: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .site-info {{
            background-color: #f1f1f1;
            color: #333;
            text-align: center;
            padding: 10px 0;
            font-size: 14px;
        }}
        a {{
            color: #007bff;
            text-decoration: none;
            transition: color 0.3s ease-in-out;
        }}
        a:hover, a:focus {{
            color: #0056b3;
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="content">
        <h1>Welcome to Arxiv Day</h1>
        <div class="inner-content">
            <h2>We collect:</h2>
            {categories_info}
        </div>
        <div class="inner-content">
            <h2>What is Arxiv Day?</h2>
            <p>We are arxiv papers every 2 hours, and translate them to Chinese. Future may have API and more abilities.</p>
            <p>Source code has been be released in <a href="https://github.com/SeanMWX/ArxivDay">Github</a>.</p>
        </div>
        <div class="inner-content">
            <h2>Contact me.</h2>
            <p><a href="https://seanzou.com">Sean Zou</a></p>
        </div>
    </div>
    <div class="site-info">
        Xinhai (Sean) Zou. <br/>
        This website does not contain any JavaScript code. <br/>
    </div>
</body>
</html>
        """

def run():
    config = Config()
    port = config.server_port()
    server_address = ('', port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"Starting httpd on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()