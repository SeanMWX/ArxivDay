import os
import json
import configparser
from datetime import datetime

import aiohttp
import aiohttp_jinja2
import jinja2
from aiohttp import web


class CaseSensitiveConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr):
        return optionstr


class Config:
    """Load server and API settings from config.ini or env."""

    def __init__(self, filename: str = "config.ini"):
        self.config = CaseSensitiveConfigParser()
        self.config.read(filename)

    def server_port(self) -> int:
        return int(self.config["server"].get("port", 80))

    def api_base_url(self) -> str:
        base = os.getenv("API_BASE_URL") or self.config["api"].get("base_url", "")
        base = base.rstrip("/")
        if not base:
            raise RuntimeError("API base_url not configured")
        return base

    def api_key(self) -> str:
        key = os.getenv("API_KEY") or self.config["api"].get("key")
        if not key:
            raise RuntimeError("API key not configured")
        return key


async def api_get(app, path: str, params=None):
    """Call data API and return JSON, raising 502 on failure."""
    session: aiohttp.ClientSession = app["http_session"]
    base = app["api_base"]
    url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
    try:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise web.HTTPBadGateway(reason=f"API {resp.status}: {text}")
            return await resp.json()
    except Exception as exc:
        raise web.HTTPBadGateway(reason=f"API request failed: {exc}") from exc


def parse_updated_field(items):
    """Convert string timestamps to datetime for template strftime usage."""
    for item in items:
        ts = item.get("updated")
        if ts and isinstance(ts, str):
            ts_clean = ts.rstrip("Z")
            try:
                item["updated"] = datetime.fromisoformat(ts_clean)
            except Exception:
                pass
    return items


async def index(request):
    app = request.app
    latest_resp = await api_get(app, "/latest")
    latest_update = latest_resp.get("date")
    count = latest_resp.get("count", 0)

    categories_resp = await api_get(app, "/categories")
    categories = categories_resp.get("categories", [])

    counts_resp = await api_get(app, "/categories/counts", params={"date": latest_update} if latest_update else None)
    categories_info = {item["category"]: item.get("count", 0) for item in counts_resp.get("items", [])}
    for cat in categories:
        categories_info.setdefault(cat, 0)

    return aiohttp_jinja2.render_template(
        "index.html",
        request,
        {"title": "Arxiv Day", "latest_update": latest_update, "count": count, "categories_info": categories_info},
    )


async def handle_404(request):
    return aiohttp_jinja2.render_template("404.html", request, {}, status=404)


async def article_handler(request):
    app = request.app
    selected_date = request.query.get("date")

    categories_resp = await api_get(app, "/categories")
    categories = categories_resp.get("categories", [])

    # Fetch a large batch (API has no enforced upper cap now)
    params = {"page_size": 1000}
    if selected_date:
        params["date"] = selected_date

    articles_resp = await api_get(app, "/articles", params=params)
    articles = parse_updated_field(articles_resp.get("items", []))

    return aiohttp_jinja2.render_template(
        "article.html",
        request,
        {
            "title": "Arxiv: TODAY" if not selected_date else f"Arxiv: {selected_date}",
            "categories": json.dumps(categories),
            "articles": articles,
            "path": "",
        },
    )


async def calendar_handler(request):
    app = request.app

    categories_resp = await api_get(app, "/categories")
    categories = categories_resp.get("categories", [])

    calendar_resp = await api_get(app, "/calendar")
    years_with_articles = calendar_resp.get("years", [])
    days_with_articles = calendar_resp.get("days", [])

    return aiohttp_jinja2.render_template(
        "calendar.html",
        request,
        {
            "title": "Arxiv Day: Calendar",
            "categories": categories,
            "years_with_articles": years_with_articles,
            "days_with_articles": days_with_articles,
        },
    )


async def favorites_handler(request):
    return aiohttp_jinja2.render_template(
        "favorites.html",
        request,
        {
            "title": "My Favorites",
        },
    )


async def archive_handler(request):
    return aiohttp_jinja2.render_template(
        "archive.html",
        request,
        {
            "title": "Archived Favorites",
        },
    )


async def storage_handler(request):
    return aiohttp_jinja2.render_template(
        "storage.html",
        request,
        {
            "title": "Local Storage",
        },
    )


async def init_app():
    """Initializes and returns the web application backed by the data API."""
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader("templates"))
    cfg = Config("config.ini")

    app["config"] = cfg
    app["api_base"] = cfg.api_base_url()
    app["http_session"] = aiohttp.ClientSession(headers={"X-API-Key": cfg.api_key()})

    app.router.add_get("/", index)
    app.router.add_get("/articles", article_handler)
    app.router.add_get("/calendar", calendar_handler)
    app.router.add_get("/favorites", favorites_handler)
    app.router.add_get("/archive", archive_handler)
    app.router.add_get("/profile", storage_handler)
    app.router.add_get("/storage", storage_handler)  # alias
    app.router.add_get("/{tail:.*}", handle_404)

    async def close_session(app):
        await app["http_session"].close()

    app.on_cleanup.append(close_session)
    return app


if __name__ == "__main__":
    port = Config("config.ini").server_port()
    app = init_app()
    web.run_app(app, port=port)
