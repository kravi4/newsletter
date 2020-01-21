from newsapi import NewsApiClient
import boto3
from os import environ
import io
import os
import sys
import subprocess
from contextlib import closing
import pydub
from pydub import AudioSegment
from pydub.playback import play


# have to anonymize this later
KEY = "AKIATZK5PR5YTEKSKP5Q"
SECRET = "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"
BUCKET = "snapjot-images"
REGION = "us-west-2"

news_api_key="915217c3b0e343039cc3859ff8445d8a"
S3_KEY = KEY
S3_SECRET = SECRET
S3_BUCKET = BUCKET
S3_REGION = REGION


# Initializing news api 
newsapi = NewsApiClient(api_key=news_api_key)

# Setting up Polly
polly = boto3.client('polly', region_name=S3_REGION, aws_access_key_id=S3_KEY, aws_secret_access_key=S3_SECRET)


def get_headlines():

    # Getting the top headlines
    top_headlines = newsapi.get_top_headlines(language='en', country='us')

    return top_headlines

# writes the audio to file
def audio_write(response, name):
    if "AudioStream" in response:
        # Note: Closing the stream is important because the service throttles on the
        # number of parallel connections. Here we are using contextlib.closing to
        # ensure the close method of the stream object will be called automatically
        # at the end of the with statement's scope.
        with closing(response["AudioStream"]) as stream:
            output = os.path.join(os.getcwd(), name+'.mp3')
            print(output)

            try:
                # Open a file for writing the output as a binary stream
                with open(output, "wb") as file:
                    file.write(stream.read())
            except IOError as error:
                # Could not write to file, exit gracefully
                print(error)
                sys.exit(-1)

    else:
        # The response didn't contain audio data, exit gracefully
        print("Could not stream audio")
        sys.exit(-1)

# generates the mp3 from the text files
def generate_speech_samples(headlines):
    num_of_headlines = len(headlines['articles'])
    titles = ["title_"+str(i) for i in range(num_of_headlines)]
    descriptions = ["description_"+str(i) for i in range(num_of_headlines)]

    for ind, dic in enumerate(headlines['articles']):
        title_response = polly.synthesize_speech(Engine='neural', Text=dic['title'], OutputFormat="mp3",  VoiceId="Matthew")
        desrip_response = polly.synthesize_speech(Engine='neural', Text=dic['description'], OutputFormat="mp3",  VoiceId="Matthew")
        audio_write(title_response, titles[ind])
        audio_write(desrip_response, descriptions[ind])


if __name__ == '__main__':
    headlines =  get_headlines()
    generate_speech_samples(headlines)


# -------------- Opens Itunes to play the audio --------------------------------------
# # Play the audio using the platform's default player
# if sys.platform == "win32":
#     os.startfile(output)
# else:
#     # The following works on macOS and Linux. (Darwin = mac, xdg-open = linux).
#     opener = "open" if sys.platform == "darwin" else "xdg-open"
#     subprocess.call([opener, output])