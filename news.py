import requests
import csv
import json
from pprint import pprint
import configparser
import boto3
from pydub import AudioSegment
from datetime import datetime
from newsapi.newsapi_client import NewsApiClient
import os
import smtplib, ssl
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase


HEADLINE_COUNT = 8
WELCOME_FILENAME = 'welcome.mp3'
GOODBYE_FILENAME = 'goodbye.mp3'
#WELCOME_MESSAGE = 'Good Morning! And welcome to your morning minutes. Here are the top headlines for ' + str(datetime.today().strftime('%A %B %d')) + '\n\n\n'
WELCOME_MESSAGE = 'Good Morning! And welcome to your morning minutes. Here are the top headlines for Friday, January 31st'
GOODBYE_MESSAGE = 'This concludes your morning minutes. Have a nice day and see you again tomorrow!'

config = configparser.ConfigParser()
config.read('config.cfg')

S3_KEY = config['S3']['KEY']
S3_SECRET = config['S3']['SECRET']
S3_BUCKET = config['S3']['BUCKET']
S3_REGION = config['S3']['REGION']

SENDER_EMAIL = "morningminits@gmail.com"

MAILING_LIST = "mailinglist.csv"

acceptable_sources = ['abc-news', 'associated-press', 'bbc-news', 'bleacher-report',
                      'bloomberg', 'business-insider', 'cbs-news', 'cnbc', 'cnn',
                      'entertainment-weekly', 'espn', 'fortune', 'google-news', 'national-geographic',
                      'nbc-news', 'newsweek', 'new-york-magazine', 'politico', 'reuters', 'techcrunch',
                      'the-hill', 'the-huffington-post', 'the-verge', 'the-wall-street-journal',
                      'the-washington-post', 'the-washington-times', 'time', 'usa-today', 'vice-news',
                      'wired']

acceptable_sources_string = ','.join(acceptable_sources)

# news api token
newsapi = NewsApiClient(api_key='915217c3b0e343039cc3859ff8445d8a')

def main():
       payload = make_news_api_request()
       urls, headlines = extract_minits(payload, False)

       receiverEmailList = []
       with open(MAILING_LIST) as csvfile:
           receiverEmailList = list(csv.reader(csvfile))# change contents to float

       print("Creating an email for: " + str(receiverEmailList))

       create_welcome_goodbye()
       print('Joining individual files to make morning minits')
       morning_minits = AudioSegment.from_mp3(WELCOME_FILENAME)

       for i in range(HEADLINE_COUNT):
              morning_minits += AudioSegment.from_mp3('source' + str(i) + '.mp3')
              morning_minits += AudioSegment.from_mp3('headline' + str(i) + '.mp3')

       morning_minits += AudioSegment.from_mp3(GOODBYE_FILENAME)
       background_music = AudioSegment.from_mp3('newsmusic.mp3') - 25
       output = background_music.overlay(morning_minits, position=3000)
       output = truncate_audio(output, 0, 20)

       today = str(datetime.today().strftime('%m-%d-%Y'))

       outputFileName = str('todays_minits'+ '.mp3')
       output.export(outputFileName, format='mp3')

       delete_audio_files()
       # send_emails(receiverEmailList, urls, headlines, outputFileName)


def make_news_api_request():
       top_headlines = newsapi.get_top_headlines(sources=acceptable_sources_string)
       print('Getting top headlines from news api')
       return top_headlines


def extract_minits(payload, verbose=False):
       headlines_to_convert = []
       sources_to_convert = []
       titles = []
       urls = []

       print('Pulling title, description, and source from headlines')

       article_load = payload['articles'][:HEADLINE_COUNT]
       for ind, article in enumerate(article_load):
              print('Processing headline ' + str(ind+1))
              title_split = article['title'].split('-')
              titles.append(title_split[0])
              title = '-'.join(title_split[:-1]).strip()

              description = article['description']
              source = title_split[-1].strip()
              urls.append(article['url'])

              if(verbose):
                     print()
                     print(title)
                     print(description)
                     print(source)
                     print(article['source'])
                     print()

              print('Source from title: ' + source)
              source = article['source']['name']
              print('Source: ' + source)

              cur_source = 'From ' + source + '\n\n\n'
              cur_headline = title
              cur_headline += '\n\n\n ' + description + '\n\n\n'

              headlines_to_convert.append(cur_headline)
              sources_to_convert.append(cur_source)

       print('Converting text to speech')

       count = 0
       for headline in headlines_to_convert:
              print('Processing headline ' + str(count+1))

              response = run_polly("Matthew", headline)
              create_response_file('headline' + str(count) + '.mp3', response)

              count += 1

       count = 0
       for source in sources_to_convert:
              print('Processing source ' + str(count+1))

              response = run_polly("Joanna", source)
              create_response_file('source' + str(count) + '.mp3', response)

              count += 1

       return urls, titles


def send_emails(receiverEmailList, articleUrls, articleHeadlines, filename):
    password = input("Enter password for morningminits@gmail.com:")

    print("Creating emails")

    subject = "Morning Minits"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL

    html = """\
    <html>
      <body>
        <img src="https://minits-setup.s3-us-west-2.amazonaws.com/banner1.png" >
        <p>
            <br>

            <p> </p>
            <a href={LINK_1} ><center> {HEADLINE_1} </center></a> <br>
            <a href={LINK_2} ><center> {HEADLINE_2} </center></a> <br>
            <a href={LINK_3} ><center> {HEADLINE_3} </center></a> <br>
            <a href={LINK_4} ><center> {HEADLINE_4} </center></a> <br>
            <a href={LINK_5} ><center> {HEADLINE_5} </center></a> <br>
            <a href={LINK_6} ><center> {HEADLINE_6} </center></a> <br>
            <a href={LINK_7} ><center> {HEADLINE_7} </center></a> <br>
            <a href={LINK_8} ><center> {HEADLINE_8} </center></a> <br>
            <a href={LINK_9} ><center> {HEADLINE_9} </center></a> <br>
            <a href={LINK_10} ><center> {HEADLINE_10} </center></a> <br>

        </p>
      </body>
    </html>
    """

    for i in range(10):
        linkPlaceholder = '{LINK_' + str(i+1) + '}'
        headlinePlaceholder = '{HEADLINE_' + str(i+1) + '}'

        linkActual = str("\"" + str(articleUrls[i]) + "\"")
        headlineActual = str(articleHeadlines[i])

        html = html.replace(linkPlaceholder, linkActual)
        html = html.replace(headlinePlaceholder, headlineActual)

    part1 = MIMEText(html, "html")

    attachment = open(filename, "rb")
    part2 = MIMEBase("application", "octet-stream")
    part2.set_payload(attachment.read())

    # Encode file in ASCII characters to send by email
    encoders.encode_base64(part2)

    # Add header as key/value pair to attachment part
    part2.add_header(
        "Content-Disposition",
        "attachment; filename= " + filename,
    )

    message.attach(part1)
    message.attach(part2)

    print("Sending emails")

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, password)
        for receiverEmail in receiverEmailList:
            message["To"] = receiverEmail[0]
            server.sendmail(
                SENDER_EMAIL, receiverEmail, message.as_string()
            )


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

       for i in range(HEADLINE_COUNT):
              os.remove('source' + str(i) + '.mp3')

       os.remove(WELCOME_FILENAME)
       os.remove(GOODBYE_FILENAME)


def truncate_audio(audio, minutes, seconds):
       if(minutes == 0 and seconds == 0):
              return audio

       end_time = (minutes*60*1000+seconds*1000) * -1
       return audio[:end_time]


if __name__ == '__main__':
       main()
