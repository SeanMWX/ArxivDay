# Arxiv Day
Arxiv Day 是一个自动化工具，用于从arXiv网站抓取最新的学术论文，并使用ChatGPT将论文的标题和摘要翻译成中文。此工具旨在为研究人员、学生和任何对最新科学研究感兴趣的人提供便捷的方式，以获取并阅读最新的研究成果的中文摘要。它还包含一个简单的Web服务器，用于展示最新收录的论文摘要。

[点击进入 Arxiv Day](http://arxivday.com)  

[【ArxivDay】如何优雅地每日查看Arxiv的文章？](https://www.bilibili.com/video/BV1zm41167We) <b>【这篇文章只适用于Arxiv Day v1】</b>，如果对Arxiv Day v1感兴趣，[请点击此处](https://github.com/SeanMWX/ArxivDay/tree/v1)。

## 2025年12月11日更新
进入 Arxiv Day v3时代。还在持续更新中...

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

### 4. 登录Mysql添加数据库
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

### 5. 修改配置文件`config.ini`
#### 5.1 api
```
[database]
host=<YOUR-DATABASE-HOST-HERE>  # 如果是本地则写localhost
user=<YOUR-DATABASE-USER-HERE>
password=<YOUR-DATABASE-PASSWORD-HERE>
database=arxiv

[settings]
arxiv_table=arxiv_daily
categories=cs.AI, cs.CR, cs.LG

[api]
key=<MAKE_YOUR_OWN_KEY_HERE>    # 用于和server 通讯

[server]
port=8000
```

#### 5.2 arxiv_auto
```
[database]
host=<YOUR-DATABASE-HOST-HERE>  # 如果是本地则写localhost
user=<YOUR-DATABASE-USER-HERE>
password=<YOUR-DATABASE-PASSWORD-HERE>
database=arxiv

[settings]
max_results=3
arxiv_table=arxiv_daily
categories=cs.AI, cs.CR, cs.LG

[schedule]
frequency_hours=2

[chatgpt]
api_key=<YOUR-OPENAI-API-KEY-HERE>  # OpenAI的密钥，可以是个人的（sk-xxxx），也可以是project的（sk-proj-xxx）
```

#### 5.3 server
```
[server]
port=80

[api]
base_url=<YOUR_API_URL>             # 自己的api地址
key=<YOUR_API_KEY>                  # api的config.ini 里面的key
```

### 6. 运行
打开三个命令行窗口，一个运行`arxiv_auto.py`以定时从arxiv收录文章，另一个运行`server.py`提供Web界面，最后一个运行从`data_api.py`作为arxiv_auto 和 server 之间的bridge，作为API的功能

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

- 第三个窗口运行data_api.py，会给server提供api接口：

    对于Windows：
    ```
    .\arxiv\Scripts\activate
    .\arxiv\Scripts\python3 data_api.py
    ```

    对于Linux：
    ```
    source arxiv/bin/activate
    arxiv/bin/python3 data_api.py
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
- 2025年12月9日，时隔一年半想起来了这个项目，由于以前的ArxivDay框架三合一都在一个服务器，收集arxiv和web容器运行，导致每次进入都实在太卡了，于是现在分割成了3个功能放到了3个不同的服务器下面（当然还是可以都在一个）
- 2025年12月11日，三个服务重构结束，收集arxiv文章放在arxiv_auto，web前端放在server，最后api提供api接口连接arxiv_auto和web前端server，同时优化了一部分web前端的功能，现在有一个accountless的同步功能，和优化了`/articles.html`页面的预览可以键盘上下翻动和左右收藏。

## TODO: fix
1. <del>（已完成）从单一的syn server.py架构，可能会考虑NodeJS，更加合理的asyn架构</del>
2. <del>（已完成）由于数据库架构问题，重复收录paper于不同的数据库中，比如一个文章同时属于cs.AI和cs.CR，则会同时收录在两个数据库中，更改数据库架构问题，提高扩展性。</del>
3. <del>（已完成）选取日期，当前不能选取日期很奇怪</del>
4. <del>（已完成）Filter过滤器</del>

## 未来功能
1. 挑选文章 -> 全文解读 （ChatGPT接口，或者月之暗面，2M上下文）
2. 导出文章引用（文献？）
3. arxiv-sanity未来参考，文章推荐
4. 知识蒸馏，知识图谱，日、月、年趋势 
5. 简化安装步骤，多个mysql表实在太蠢了，考虑Docker等。
