from newsapi import NewsApiClient
from dotenv import load_dotenv
from datetime import date
import os
import json
import requests

# init
load_dotenv()
API_KEY = os.getenv('NEWS_API_KEY')

api = NewsApiClient(api_key=API_KEY)
today_date = date.today()

# headlines = api.get_top_headlines(country="sg")
everything = api.get_everything(from_param="2023-05-11", to="2023-05-13", domains="bbc.co.uk", sort_by="popularity")
print(everything)
with open('debug.txt', 'w', encoding='utf-8') as f:
    f.write(json.dumps(everything, indent=4))
