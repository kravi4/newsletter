import requests
import json
from pprint import pprint
import configparser
import boto3
from pydub import AudioSegment
from datetime import datetime
import os


HEADLINE_COUNT = 10
WELCOME_FILENAME = 'welcome.mp3'
GOODBYE_FILENAME = 'goodbye.mp3'
WELCOME_MESSAGE = 'Good Morning! And welcome to your morning minutes. Here are todays headlines\n\n\n'
GOODBYE_MESSAGE = 'This concludes your morning minutes. Have a nice day and see you again tomorrow!'

config = configparser.ConfigParser()
config.read('config.cfg')

S3_KEY = config['S3']['KEY']
S3_SECRET = config['S3']['SECRET']
S3_BUCKET = config['S3']['BUCKET']
S3_REGION = config['S3']['REGION']


def main():
       payload = make_news_api_request()
       urls = extract_minits(payload, True)

       create_welcome_goodbye()
       print('Joining individual files to make morning minits')
       morning_minits = AudioSegment.from_mp3(WELCOME_FILENAME)

       for i in range(HEADLINE_COUNT):
              morning_minits += AudioSegment.from_mp3('headline' + str(i) + '.mp3')

       morning_minits += AudioSegment.from_mp3(GOODBYE_FILENAME)
       background_music = AudioSegment.from_mp3('background.mp3') - 25
       output = background_music.overlay(morning_minits, position=3000)
       output = truncate_audio(output, 0, 25)

       today = str(datetime.today().strftime('%m-%d-%Y'))
       output.export('morning_minits_' + today + '.mp3', format='mp3')

       delete_audio_files()
       email_text = create_email_text(urls)
       print()
       print(email_text)


def make_news_api_request():
       url = ('https://newsapi.org/v2/top-headlines?'
              'country=us&'
              'apiKey=6ec99ad88fd9445aaa725a60436e3eef')

       print('Getting top headlines from news api')
       return requests.get(url).json()


def extract_minits(payload, verbose=False):
       headlines_to_convert = []
       urls = []

       print('Pulling title, description, and source from headlines')
       count = 0
       for article in payload['articles']:
              if(count >= HEADLINE_COUNT):
                     break
              
              print('Processing headline ' + str(count+1))

              title_split = article['title'].split('-')
              title = '-'.join(title_split[:-1]).strip()

              description = article['description']
              source = title_split[-1].strip()
              urls.append(article['url'])

              if(title == '' or description == '' or source == ''):
                     continue

              if(verbose):
                     print()
                     print(title)
                     print(description)
                     print(source)
                     print(article['source'])
                     print()

              if('.com' in source):
                     print('Source from title: ' + source)
                     source = article['source']['name']
                     print('Source: ' + source)

              cur_headline = 'From ' + source + '\n\n\n'
              cur_headline += title
              cur_headline += '\n\n\n ' + description + '\n\n\n'
              
              
              headlines_to_convert.append(cur_headline)

              count += 1

       print('Converting text to speech')
       count = 0
       voice = ''
       for headline in headlines_to_convert:
              print('Processing headline ' + str(count+1))
              
              if(count % 2 == 1):
                     voice = 'Matthew'

              else:
                     voice = 'Joanna'

              response = run_polly(voice, headline)
              create_response_file('headline' + str(count) + '.mp3', response)
              
              count += 1

       return urls


def create_email_text(urls):
       print('Creating email text')
       email_text = ['Hope you enjoyed the Morning Minits! You can find the links to the articles referenced in the minits below for further reading.\n\n']
       count = 0
       for url in urls:
              email_text.append('Article ' + str(count+1) + ': ' + url + '\n\n')
              count += 1

       return ''.join(email_text)


def create_welcome_goodbye():
       print('Creating welcome message')
       welcome_response = run_polly('Matthew', WELCOME_MESSAGE)
       create_response_file(WELCOME_FILENAME, welcome_response)

       print('Creating goodbye message')
       goodbye_response = run_polly('Joanna', GOODBYE_MESSAGE)
       create_response_file(GOODBYE_FILENAME, goodbye_response)


def run_polly(voice, text):
       polly = boto3.client('polly', region_name=S3_REGION, aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)
       
       return polly.synthesize_speech(
              Engine = 'neural',
              OutputFormat = 'mp3',
              Text = text,
              VoiceId = voice
       )


def create_response_file(filename, response):
       file = open(filename, 'wb')
       file.write(response['AudioStream'].read())
       file.close()


def delete_audio_files():
       print('Deleting individual headline mp3s')
       for i in range(HEADLINE_COUNT):
              os.remove('headline' + str(i) + '.mp3')

       os.remove(WELCOME_FILENAME)
       os.remove(GOODBYE_FILENAME)


def truncate_audio(audio, min, sec):
       end_time = (min*60*1000+sec*1000) * -1
       return audio[:end_time]


if __name__ == '__main__':
       main()