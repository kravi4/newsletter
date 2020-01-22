import requests
import json
from pprint import pprint
import configparser
import boto3
from pydub import AudioSegment
from datetime import datetime
​
​
def main():
       news_byte = AudioSegment.from_mp3('news.mp3')
       background_music = AudioSegment.from_mp3('background.mp3') - 20
​
       output = news_byte.overlay(background_music, position=1000)
       today = str(datetime.today().strftime('%m-%d-%Y'))
       output.export('news_byte_' + today + '.mp3', format="mp3")
​
​
def get_news_byte():
       config = configparser.ConfigParser()
       config.read('config.cfg')
​
       S3_KEY = config['S3']['KEY']
       S3_SECRET = config['S3']['SECRET']
       S3_BUCKET = config['S3']['BUCKET']
       S3_REGION = config['S3']['REGION']
​
​
       url = ('https://newsapi.org/v2/top-headlines?'
              'country=us&'
              'apiKey=6ec99ad88fd9445aaa725a60436e3eef')
​
       response = requests.get(url).json()
       top_ten_headlines = []
       string_to_translate = ['Good Morning! Here are the top ten headlines for today.\n\n\n']
​
       count = 0
       for article in response['articles']:
              if(count >= 10):
                     break
​
              cur_news_obj = {}
​
              title_split = article['title'].split('-')
              description = article['description']
              source = title_split[-1].strip()
              title_split.pop()
              title = '-'.join(title_split).strip()
​
              if(description == '' or title == '' or source == ''):
                     continue
​
              string_to_translate.append('Headline number ' + str(count + 1) + '\n\n\n\n' + title)
              string_to_translate.append('\n\n\n\n ' + description + '\n\n\n\n')
              string_to_translate.append('This article was from ' + source + '\n\n\n\n')
​
              count += 1
​
​
       print(''.join(string_to_translate))
​
​
       polly = boto3.client('polly', region_name=S3_REGION, aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)
​
       response = polly.synthesize_speech(
       Engine = 'neural',
       OutputFormat = 'mp3',
       Text = ''.join(string_to_translate),
       VoiceId = 'Matthew'
       )
​
       file = open('news.mp3', 'wb')
       file.write(response['AudioStream'].read())
       file.close()
​
​
if __name__ == '__main__':
       # get_news_byte()
       main()
			