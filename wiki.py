import json
import requests
import urllib.parse as parse

def find_page(search_string):
    url = "https://en.wikipedia.org/w/api.php?action=query&format=json&generator=search&gsrsearch={0}"
    url = url.format(parse.quote(search_string))

    content = requests.get(url).content
    content = json.loads(content)

    page = None
    if "query" in content:
        if "pages" in content["query"]:
            pages = content["query"]["pages"]
            for entry in pages:
                if pages[entry]["index"] == 1:
                    page = pages[entry]
                    page = {
                        "id": page["pageid"],
                        "title": page["title"]
                    }
    

    return page

def get_summary(page):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/{0}"
    url = url.format(parse.quote(page["title"]))

    content = requests.get(url).content
    content = json.loads(content)

    summary = {
        "extract": content["extract"],
        "url": content["content_urls"]["desktop"]["page"]
    }

    if "thumbnail" in content:
        summary["thumbnail"] = content["thumbnail"]["source"]
    else:
        summary["thumbnail"] = None

    return summary