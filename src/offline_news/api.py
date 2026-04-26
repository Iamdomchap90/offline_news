from ninja import NinjaAPI

api = NinjaAPI(title="Offline News API", version="1.0.0")

from articles.api import router as articles_router  # noqa: E402

api.add_router("/articles", articles_router)
