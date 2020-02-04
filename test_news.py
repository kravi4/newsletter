import requests
import csv
import json
from pprint import pprint
import configparser
import boto3
from pydub import AudioSegment
from datetime import datetime
from newsapi import NewsApiClient
import pandas as pd

# news api token
newsapi = NewsApiClient(api_key='915217c3b0e343039cc3859ff8445d8a')

p_df = pd.read_csv("personalizationlist.csv")
list_of_lists = p_df.to_numpy().tolist()

for this in list_of_lists:
	for niche in this[1:]:
		query = newsapi.get_everything(q="+"+niche, language = 'en', page_size = 100, sort_by='relevancy')
		print(niche +": "+str(query['articles'][:10]))



# top_headlines = newsapi.get_top_headlines()