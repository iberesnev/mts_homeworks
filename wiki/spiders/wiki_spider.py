import re

from wiki.items import WikiItem
import scrapy


class WikiSpiderSpider(scrapy.Spider):
    name = "wiki_spider"
    allowed_domains = ["ru.wikipedia.org", "www.imdb.com"]
    start_urls = ["https://ru.wikipedia.org/wiki/Категория:Фильмы_по_алфавиту"]

    def __init__(self, max_pages="2", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_pages = int(max_pages)

    def parse(self, response, counter=0):
        film_hrefs = response.css("#mw-pages .mw-category-group ul li a::attr(href)").getall()
        for href in film_hrefs:
            yield response.follow(href, callback=self.parse_film)

        next_page = response.xpath(
            "//div[@id='mw-pages']//a[normalize-space()='Следующая страница']/@href"
        ).get()
        if next_page and counter < self.max_pages - 1:
            yield response.follow(next_page, callback=self.parse, cb_kwargs={"counter": counter + 1})

    def parse_film(self, response):
        item = WikiItem()
        item["title"] = self._clean(response.css("span.mw-page-title-main::text").get())
        item["genre"] = self._infobox_value(response, ["Жанр", "Жанры"])
        item["director"] = self._infobox_value(response, ["Режиссёр", "Режиссер", "Режиссеры", "Режиссёры"])
        item["country"] = self._infobox_value(response, ["Страна", "Страны"])
        item["year"] = self._extract_year(self._infobox_value(response, ["Год", "Годы"]))

        imdb_url = self._extract_imdb_url(response)

        # если это явно не карточка фильма — не сохраняем
        if not any([item.get("genre"), item.get("director"), item.get("country"), item.get("year")]):
            return

        if imdb_url:
            yield scrapy.Request(
                url=response.urljoin(imdb_url),
                callback=self.parse_imdb_rating,
                cb_kwargs={"item": item},
                priority=100,
            )
        else:
            item["imdb_rating"] = None
            yield item

    def parse_imdb_rating(self, response, item):
        # капча/блокировки
        if response.status == 403 or "captcha" in response.text.lower():
            self.logger.warning(f"IMDB блокирует доступ для {item['title']}. URL: {response.url}")
            item["imdb_rating"] = "BLOCKED"
            yield item
            return

        rating = response.css('div[data-testid="hero-rating-bar__aggregate-rating__score"] span::text').get()

        if not rating:
            rating = response.css('span.sc-4dc495c1-1.lbQcRY::text').get()

        if not rating:
            # грубый фолбэк
            for text in response.css("*::text").getall():
                t = text.strip()
                if re.match(r"^\d+\.\d+$", t) and len(t) <= 4:
                    rating = t
                    break

        if rating:
            m = re.search(r"(\d+\.\d+)", rating.strip())
            item["imdb_rating"] = m.group(1) if m else rating.strip()
        else:
            item["imdb_rating"] = None

        yield item

    def _extract_imdb_url(self, response):
        imdb_link = response.xpath(
            '//a[contains(@href, "imdb.com") and contains(@href, "/title/tt")]/@href'
        ).get()
        if imdb_link:
            return response.urljoin(imdb_link)

        imdb_link = response.xpath(
            '//a[contains(text(), "IMDB") or contains(text(), "imdb")]/@href'
        ).get()
        return response.urljoin(imdb_link) if imdb_link else None

    def _infobox_value(self, response, labels):
        for label in labels:
            td = response.xpath(
                "//table[contains(@class,'infobox')]"
                f"//tr[th[contains(normalize-space(.), {self._xpath_literal(label)})]]/td"
            )
            if td:
                texts = td.xpath(
                    ".//text()[not(ancestor::style) and not(ancestor::script) and not(ancestor::sup)]"
                ).getall()
                text = self._clean(" ".join(texts))
                if text:
                    return text
        return None

    def _extract_year(self, text):
        if not text:
            return None
        m = re.search(r"\b(18\d{2}|19\d{2}|20\d{2}|2100)\b", text)
        return m.group(1) if m else None

    def _clean(self, s):
        if not s:
            return None
        s = re.sub(r"\s+", " ", s).strip()
        return s or None

    def _xpath_literal(self, s: str) -> str:
        if "'" not in s:
            return f"'{s}'"
        if '"' not in s:
            return f'"{s}"'
        parts = s.split("'")
        return "concat(" + ",\"'\",".join([f"'{p}'" for p in parts]) + ")"