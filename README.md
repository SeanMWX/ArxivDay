# Arxiv Day
Arxiv Day 是一个自动化工具，用于从arXiv网站抓取最新的学术论文，并使用ChatGPT将论文的标题和摘要翻译成中文。此工具旨在为研究人员、学生和任何对最新科学研究感兴趣的人提供便捷的方式，以获取并阅读最新的研究成果的中文摘要。它还包含一个简单的Web服务器，用于展示最新收录的论文摘要。

[点击进入 Arxiv Day](http://arxivday.com)  

[【ArxivDay】如何优雅地每日查看Arxiv的文章？](https://www.bilibili.com/video/BV1zm41167We) <b>【这篇文章只适用于Arxiv Day v1】</b>，如果对Arxiv Day v1感兴趣，[请点击此处](https://github.com/SeanMWX/ArxivDay/tree/v1)。

## 2025年12月9日
正在更新 Arxiv Day v3。

## 2024年4月3日更新
进入 Arxiv Day v2时代。

## 如何使用？
### 1. 克隆仓库
```
git clone https://github.com/SeanMWX/ArxivDay
cd ArxivDay
```

### 2. 配置Python虚拟环境
对于Windows：
```
python -m venv arxiv
.\arxiv\Scripts\activate
```

对于Linux：
```
python3 -m venv arxiv
source arxiv/bin/activate
```

安装依赖：
```
pip install -r requirements.txt
```

### 3. 配置Mysql环境
- 对于Windows：

    1. 下载并安装MySQL：访问[MySQL官方网站](https://dev.mysql.com/downloads/mysql/)下载MySQL Community Server。
    2. 配置：安装向导将引导你完成配置过程，包括配置数据库的root密码。
    3. 启动MySQL服务：安装完成后，MySQL服务应该已经启动。你可以在“服务”应用程序中查看服务状态。

- 对于Linux  (Ubuntu/Debian):

    安装MySQL，运行安全配置脚本，检查MySQL服务状态：
    ```
    sudo apt update                      # 检查apt更新
    sudo apt install mysql-server        # 安装MySQL
    sudo mysql_secure_installation       # 运行安全配置脚本
    sudo systemctl status mysql          # 检查MySQL服务状态
    ```

### 4. 修改配置文件`config.ini`
```
[database]
host=localhost                   # 不用动
user=seanzou                     # 写自己的username
password=19970308                # 写自己的密码
database=arxiv                   # 不建议动

[settings]
max_results = 500                # 单次搜索最新的500篇文章
arxiv_table=arxiv_daily          # 收录文章的表格名称见`### 5. 登录Mysql添加数据库`
categories=cs.AI, cs.CR, cs.LG   # 需要收录的category

[schedule]
frequency_hours=2                # 每过2个小时收录一次arxiv

[server]
port=80                          # web服务器在端口80打开

[chatgpt]
api_key=sk-xxxxxx                # 你的ChatGPT API Key
```

### 5. 登录Mysql添加数据库
我们需要为我们的python添加一些数据库环境。

创建一个用户（最好不要用root用户）
```
CREATE USER 'seanzou'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON arxiv.* TO 'seanzou'@'localhost';
FLUSH PRIVILEGES;
```

登录MySQL
```
mysql -u <username> -p<password>
```

创建arxiv数据库
```
CREATE DATABASE arxiv
```

添加arxiv_daily表格
```
CREATE TABLE arxiv_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    authors TEXT,
    categories TEXT,
    comment TEXT,
    doi VARCHAR(255),
    entry_id VARCHAR(255),
    journal_ref VARCHAR(255),
    links TEXT,
    primary_category VARCHAR(255),
    published DATETIME,
    summary TEXT,
    title VARCHAR(255),
    updated DATETIME,
    CN_title TEXT,
    CN_summary TEXT
);
```

### 6. 运行
打开两个命令行窗口，一个运行`arxiv_auto.py`以定时从arxiv收录文章，另一个运行`server.py`提供Web界面。

- 第一个窗口运行arxiv_auto.py，每一段时间从arxiv收录：

    对于Windows：
    ```
    .\arxiv\Scripts\activate
    .\arxiv\Scripts\python3 arxiv_auto.py
    ```

    对于Linux：
    ```
    source arxiv/bin/activate
    arxiv/bin/python3 arxiv_auto.py
    ```

- 第二个窗口运行server.py，提供web UI，打开"localhost:80"：

    对于Windows：
    ```
    .\arxiv\Scripts\activate
    .\arxiv\Scripts\python3 asyn_server.py
    ```

    对于Linux：
    ```
    source arxiv/bin/activate
    arxiv/bin/python3 asyn_server.py
    ```

## 注意事项
1. 确保安装了MySQL、Python等必备软件。
2. 确保安装了所有依赖项，使用pip install -r requirements.txt命令。
3. 根据配置文件config.ini调整MySQL用户名、密码、服务器端口等信息。

## History:

- 2024年3月24日，[ArxivDay](http://arxivday.com)上线
- 2024年3月26日，[Github-ArxivDay](https://github.com/SeanMWX/ArxivDay)上线
- 2024年3月27日，增加asyn服务器[asyn_server.py](https://github.com/SeanMWX/ArxivDay/blob/main/asyn_server.py)
- 2024年4月3日，由于迭代太快，进入了v2时代，如果从B站这个视频[【ArxivDay】如何优雅地每日查看Arxiv的文章？](https://www.bilibili.com/video/BV1zm41167We)来的，请参考下载[v1.0.1](https://github.com/SeanMWX/ArxivDay/releases/tag/v1.0.1)，v2时代合并所有category表，并且提供了一个`/calendar.html`的日历页面，在`/articles.html`的文章页面是提供了category的分类过滤器

## TODO: fix
1. <del>（已完成）从单一的syn server.py架构，可能会考虑NodeJS，更加合理的asyn架构</del>
2. <del>（已完成）由于数据库架构问题，重复收录paper于不同的数据库中，比如一个文章同时属于cs.AI和cs.CR，则会同时收录在两个数据库中，更改数据库架构问题，提高扩展性。</del>

1. 简化安装步骤，多个mysql表实在太蠢了，考虑Docker等。

## 未来功能
1. <del>（已完成）选取日期，当前不能选取日期很奇怪</del>
2. <del>（已完成）Filter过滤器</del>

1. 挑选文章 -> 全文解读 （ChatGPT接口，或者月之暗面，2M上下文）
2. 导出文章引用（文献？）
3. arxiv-sanity未来参考，文章推荐
4. 知识蒸馏，知识图谱，日、月、年趋势 
