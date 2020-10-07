import requests
import json
import os
from discord import Embed
from urllib.parse import quote

COLORS = {
    "mod-negative": 15746887, # red
    "mod-positive": 4437377,  # green
    "mod-neutral": 7506394,   # blue
    "profile-card": 15105570  # orange
}

API_KEY = "cd4b7e46"
API = {
    "search": "http://www.omdbapi.com/?apikey={0}&s={1}",
    "load": "http://www.omdbapi.com/?apikey={0}&i={1}"
}

def search(search_str):
    fstr = quote(search_str)
    url = API["search"].format(API_KEY, fstr)

    res = requests.get(url).content
    res = json.loads(res)

    if len(res["Search"]) == 0:
        return None

    embed = Embed(
        title='Search: "{0}"'.format(search_str),
        color=COLORS["profile-card"]
    ).set_author(name="IMBD", url="https://www.imdb.com/", icon_url="https://i.ibb.co/YhGHsYz/imbd.png")

    entries = []
    for i in range(0, len(res["Search"])):
        entry = res["Search"][i]

        embed.add_field(
            name="**{0}.** {1} ({2})".format(i+1, entry["Title"], entry["Year"]),
            value="https://www.imdb.com/title/{0}/".format(entry["imdbID"])
        )
    
    return embed

def load(search_str, n):
    fstr = quote(search_str)
    url = API["search"].format(API_KEY, fstr)

    res = requests.get(url).content
    res = json.loads(res)

    if len(res["Search"]) == 0:
        raise KeyError
    
    try:
        movie_id = res["Search"][n-1]["imdbID"]
    except:
        raise IndexError

    url = API["load"].format(API_KEY, movie_id)
    res = requests.get(url).content
    movie = json.loads(res)

    description = movie["Plot"]
    embed = Embed(
        title="{0}".format(movie["Title"]),
        color=COLORS["profile-card"]
    ).set_author(
        name="IMBD", 
        url="https://www.imdb.com/title/{0}/".format(movie["imdbID"]), 
        icon_url="https://i.ibb.co/YhGHsYz/imbd.png"
    ).set_image(url=movie["Poster"])

    for field in ["Year", "Genre", "Runtime", "Actors", "Director", "Writer", "Language"]:
        embed.add_field(name=field, value=movie[field])
    
    rts = None
    for review in movie["Ratings"]:
        if review["Source"] == "Rotten Tomatoes":
            rts = review["Value"]
    
    if rts is not None:
        embed.add_field(name="Rotten Tomatoes Score", value=rts)
    
    return embed