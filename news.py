import requests
import csv
import json
from pprint import pprint
import configparser
import boto3
from pydub import AudioSegment
from datetime import datetime, timedelta
from newsapi import NewsApiClient
import os
import smtplib, ssl
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase


HEADLINE_COUNT = 8
ARTICLE_COUNT = 1
WELCOME_FILENAME = 'welcome.mp3'
GOODBYE_FILENAME = 'goodbye.mp3'
WELCOME_MESSAGE = 'Good Morning! And welcome to your morning minutes. Here are the top headlines for ' + str((datetime.today() + timedelta(days=1)).strftime('%A %B %d')) + '\n\n\n'
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
                      'the-washington-times', 'time', 'usa-today', 'vice-news', 'wired']

acceptable_sources_string = ','.join(acceptable_sources)

CATEGORIES = ['business', 'entertainment', 'health', 'science', 'technology']

# news api token
newsapi = NewsApiClient(api_key='915217c3b0e343039cc3859ff8445d8a')

def main():
    # Use below for diverse headlines
    diverse_payloads = make_news_api_request_diverse()
    general_payload = newsapi.get_top_headlines(category='general', country='us')

    count = 0

    # payload = make_news_api_request()
    extract = extract_minits(general_payload, count, general=True, verbose=True)
    urls = extract[0]
    headlines = extract[1]
    imageUrls = extract[2]
    count = extract[3]
    
    for payload in diverse_payloads:
        extract = extract_minits(payload, count, verbose=True)
        urls.append(extract[0][0])
        headlines.append(extract[1][0])
        imageUrls.append(extract[2][0])
        count = extract[3]

    create_welcome_goodbye()
    print('Joining individual files to make morning minits')
    morning_minits = AudioSegment.from_mp3(WELCOME_FILENAME)

    for i in range(HEADLINE_COUNT):
            morning_minits += AudioSegment.from_mp3('headline' + str(i) + '.mp3')

    morning_minits += AudioSegment.from_mp3(GOODBYE_FILENAME)
    background_music = AudioSegment.from_mp3('newsMusicExtended.mp3') - 25
    output = background_music.overlay(morning_minits, position=3000)
    output = truncate_audio(output, 2, 30)

    today = str(datetime.today().strftime('%m-%d-%Y'))

    outputFileName = str('todays_minits'+ '.mp3')
    output.export(outputFileName, format='mp3')

    delete_audio_files()

    receiverEmailList = []
    with open(MAILING_LIST) as csvfile:
        receiverEmailList = list(csv.reader(csvfile))# change contents to float

    print("Creating an email for: " + str(receiverEmailList))

    send_emails(receiverEmailList, urls, headlines, imageUrls, outputFileName)


def make_news_api_request():
       print('Getting top headlines from news api')
       top_headlines = newsapi.get_top_headlines(sources=acceptable_sources_string)
       return top_headlines


def make_news_api_request_diverse():
    top_headlines = []
    for category in CATEGORIES:
        print('Getting top headlines for: ' + category)
        top_headlines.append(newsapi.get_top_headlines(category=category, country='us'))

    return top_headlines


def extract_minits(payload, count, general=False, verbose=False):
       headlines_to_convert = []
       headlines = []
       urls = []
       images = []

       print('Pulling title, description, and source from headlines')
       
       headlines_to_take = ARTICLE_COUNT
       if(general):
           headlines_to_take = 3

       article_load = payload['articles'][:headlines_to_take]
       for _, article in enumerate(article_load):
              print('Processing headline ' + str(count+1))
              title_split = article['title'].split('-')
              headlines.append(title_split[0])
              title = '-'.join(title_split[:-1]).strip()

              description = article['description']
              source = title_split[-1].strip()
              urls.append(article['url'])
              images.append(article['urlToImage'])

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

              cur_headline = 'From ' + source + '\n\n\n'
              cur_headline += title
              cur_headline += '\n\n\n ' + description + '\n\n\n'

              headlines_to_convert.append(cur_headline)

       print('Converting text to speech')
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

       return [urls, headlines, images, count]


def send_emails(receiverEmailList, articleUrls, articleHeadlines, articleImages, filename):
    # password = input("Enter password for morningminits@gmail.com:")

    print("Creating emails")

    subject = "Morning Minits"

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL

    html = """\
    <html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
    <head>
        <meta charset="utf-8"> <!-- utf-8 works for most cases -->
        <meta name="viewport" content="width=device-width"> <!-- Forcing initial-scale shouldn't be necessary -->
        <meta http-equiv="X-UA-Compatible" content="IE=edge"> <!-- Use the latest (edge) version of IE rendering engine -->
        <meta name="x-apple-disable-message-reformatting">  <!-- Disable auto-scale in iOS 10 Mail entirely -->
        <meta name="format-detection" content="telephone=no,address=no,email=no,date=no,url=no"> <!-- Tell iOS not to automatically link certain text strings. -->
        <title></title> <!-- The title tag shows in email notifications, like Android 4.4. -->

        <!-- Web Font / @font-face : BEGIN -->
        <!-- NOTE: If web fonts are not required, lines 10 - 27 can be safely removed. -->

        <!-- Desktop Outlook chokes on web font references and defaults to Times New Roman, so we force a safe fallback font. -->
        <!--[if mso]>
            <style>
                * {
                    font-family: sans-serif !important;
                }
            </style>
        <![endif]-->

        <!-- All other clients get the webfont reference; some will render the font and others will silently fail to the fallbacks. More on that here: http://stylecampaign.com/blog/2015/02/webfont-support-in-email/ -->
        <!--[if !mso]><!-->
        <!-- insert web font reference, eg: <link href='https://fonts.googleapis.com/css?family=Roboto:400,700' rel='stylesheet' type='text/css'> -->
        <!--<![endif]-->

        <!-- Web Font / @font-face : END -->

        <!-- CSS Reset : BEGIN -->
        <style>

            /* What it does: Remove spaces around the email design added by some email clients. */
            /* Beware: It can remove the padding / margin and add a background color to the compose a reply window. */
            html,
            body {
                margin: 0 auto !important;
                padding: 0 !important;
                height: 100% !important;
                width: 100% !important;
            }

            /* What it does: Stops email clients resizing small text. */
            * {
                -ms-text-size-adjust: 100%;
                -webkit-text-size-adjust: 100%;
            }

            /* What it does: Centers email on Android 4.4 */
            div[style*="margin: 16px 0"] {
                margin: 0 !important;
            }

            /* What it does: forces Samsung Android mail clients to use the entire viewport */
            #MessageViewBody, #MessageWebViewDiv{
                width: 100% !important;
            }

            /* What it does: Stops Outlook from adding extra spacing to tables. */
            table,
            td {
                mso-table-lspace: 0pt !important;
                mso-table-rspace: 0pt !important;
            }

            /* What it does: Fixes webkit padding issue. */
            table {
                border-spacing: 0 !important;
                border-collapse: collapse !important;
                table-layout: fixed !important;
                margin: 0 auto !important;
            }

            /* What it does: Uses a better rendering method when resizing images in IE. */
            img {
                -ms-interpolation-mode:bicubic;
            }

            /* What it does: Prevents Windows 10 Mail from underlining links despite inline CSS. Styles for underlined links should be inline. */
            a {
                text-decoration: none;
            }

            /* What it does: A work-around for email clients meddling in triggered links. */
            a[x-apple-data-detectors],  /* iOS */
            .unstyle-auto-detected-links a,
            .aBn {
                border-bottom: 0 !important;
                cursor: default !important;
                color: inherit !important;
                text-decoration: none !important;
                font-size: inherit !important;
                font-family: inherit !important;
                font-weight: inherit !important;
                line-height: inherit !important;
            }

            /* What it does: Prevents Gmail from displaying a download button on large, non-linked images. */
            .a6S {
                display: none !important;
                opacity: 0.01 !important;
            }

            /* What it does: Prevents Gmail from changing the text color in conversation threads. */
            .im {
                color: inherit !important;
            }

            /* If the above doesn't work, add a .g-img class to any image in question. */
            img.g-img + div {
                display: none !important;
            }

            /* What it does: Removes right gutter in Gmail iOS app: https://github.com/TedGoas/Cerberus/issues/89  */
            /* Create one of these media queries for each additional viewport size you'd like to fix */

            /* iPhone 4, 4S, 5, 5S, 5C, and 5SE */
            @media only screen and (min-device-width: 320px) and (max-device-width: 374px) {
                u ~ div .email-container {
                    min-width: 320px !important;
                }
            }
            /* iPhone 6, 6S, 7, 8, and X */
            @media only screen and (min-device-width: 375px) and (max-device-width: 413px) {
                u ~ div .email-container {
                    min-width: 375px !important;
                }
            }
            /* iPhone 6+, 7+, and 8+ */
            @media only screen and (min-device-width: 414px) {
                u ~ div .email-container {
                    min-width: 414px !important;
                }
            }

        </style>

        <!-- What it does: Makes background images in 72ppi Outlook render at correct size. -->
        <!--[if gte mso 9]>
        <xml>
            <o:OfficeDocumentSettings>
                <o:AllowPNG/>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
        <![endif]-->

        <!-- CSS Reset : END -->

        <!-- Progressive Enhancements : BEGIN -->
        <style>

    	    /* What it does: Hover styles for buttons */
    	    .button-td,
    	    .button-a {
    	        transition: all 100ms ease-in;
    	    }
    	    .button-td-primary:hover,
    	    .button-a-primary:hover {
    	        background: #555555 !important;
    	        border-color: #555555 !important;
    	    }

    	    /* Media Queries */
    	    @media screen and (max-width: 600px) {

    	        /* What it does: Adjust typography on small screens to improve readability */
    	        .email-container p {
    	            font-size: 17px !important;
    	        }

    	    }

        </style>
        <!-- Progressive Enhancements : END -->

    </head>
    <!--
    	The email background color (#FFFFFF) is defined in three places:
    	1. body tag: for most email clients
    	2. center tag: for Gmail and Inbox mobile apps and web versions of Gmail, GSuite, Inbox, Yahoo, AOL, Libero, Comcast, freenet, Mail.ru, Orange.fr
    	3. mso conditional: For Windows 10 Mail
    -->
    <body width="100%" style="margin: 0; padding: 0 !important; mso-line-height-rule: exactly; background-color: #FFFFFF;">
    	<center style="width: 100%; background-color: #FFFFFF;">
        <!--[if mso | IE]>
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #FFFFFF;">
        <tr>
        <td>
        <![endif]-->

            <!-- Visually Hidden Preheader Text : BEGIN -->
            <!-- <div style="display: none; font-size: 1px; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden; mso-hide: all; font-family: sans-serif;">
                (Optional) This text will appear in the inbox preview, but not the email body. It can be used to supplement the email subject line or even summarize the email's contents. Extended text preheaders (~490 characters) seems like a better UX for anyone using a screenreader or voice-command apps like Siri to dictate the contents of an email. If this text is not included, email clients will automatically populate it using the text (including image alt text) at the start of the email's body.
            </div> -->
            <!-- Visually Hidden Preheader Text : END -->

            <!-- Create white space after the desired preview text so email clients don’t pull other distracting text into the inbox preview. Extend as necessary. -->
            <!-- Preview Text Spacing Hack : BEGIN -->
            <div style="display: none; font-size: 1px; line-height: 1px; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden; mso-hide: all; font-family: sans-serif;">
    	        &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;
            </div>
            <!-- Preview Text Spacing Hack : END -->

            <!--
                Set the email width. Defined in two places:
                1. max-width for all clients except Desktop Windows Outlook, allowing the email to squish on narrow but never go wider than 600px.
                2. MSO tags for Desktop Windows Outlook enforce a 600px width.
            -->
            <div style="max-width: 600px; margin: 0 auto;" class="email-container">
                <!--[if mso]>
                <table align="center" role="presentation" cellspacing="0" cellpadding="0" border="0" width="600">
                <tr>
                <td>
                <![endif]-->

    	        <!-- Email Body : BEGIN -->
    	        <table align="center" role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: auto;">
                    <!-- Hero Image, Flush : BEGIN -->
                    <tr>
                            <img src="https://minits-setup.s3-us-west-2.amazonaws.com/banner1.png" width="600" height="" alt="alt_text" border="0" style="width: 100%; max-width: 600px; height: auto; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555; margin: auto; display: block;" class="g-img">
                    </tr>
                    <!-- Hero Image, Flush : END -->

                    <!-- 1 Column Text + Button : BEGIN -->
                    <tr>
                        <td style="background-color: #ffffff;">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td style="padding: 20px; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555;">
                                        <h2 style="margin: 0 0 10px 0; font-family: sans-serif; font-size: 18px; line-height: 22px; color: #333333; font-weight: bold; text-align: center;"> Good Morning! </h2>
                                        <p style="margin: 0; text-align: center;">Here are your morning Minits for {DATE}</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- 1 Column Text + Button : END -->

                    <!-- 2 Even Columns : BEGIN -->
                    <tr>
                        <td style="padding: 0 10px 40px 10px; background-color: #ffffff;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_1} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                   <a href={LINK_1} style="margin: 0;">{HEADLINE_1}</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_2} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                    <a href={LINK_2} style="margin: 0;">{HEADLINE_2}</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- 2 Even Columns : END -->

                    <!-- 2 Even Columns : BEGIN -->
                    <tr>
                        <td style="padding: 0 10px 40px 10px; background-color: #ffffff;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_3} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                   <a href={LINK_3} style="margin: 0;">{HEADLINE_3}</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_4} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                    <a href={LINK_4} style="margin: 0;">{HEADLINE_4}</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- 2 Even Columns : END -->

                    <!-- 2 Even Columns : BEGIN -->
                    <tr>
                        <td style="padding: 0 10px 40px 10px; background-color: #ffffff;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_5} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                   <a href={LINK_5} style="margin: 0;">{HEADLINE_5}</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_6} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                    <a href={LINK_6} style="margin: 0;">{HEADLINE_6}</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- 2 Even Columns : END -->

                    <!-- 2 Even Columns : BEGIN -->
                    <tr>
                        <td style="padding: 0 10px 40px 10px; background-color: #ffffff;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_7} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                   <a href={LINK_7} style="margin: 0;">{HEADLINE_7}</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                    <td valign="top" width="50%">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                            <tr>
                                                <td style="text-align: center; padding: 0 10px;">
                                                    <img src={IMAGE_8} width="200" height="" alt="alt_text" border="0" style="width: 100%; max-width: 200px; background: #dddddd; font-family: sans-serif; font-size: 15px; line-height: 15px; color: #555555;">
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="text-align: left; font-family: sans-serif; font-size: 15px; line-height: 20px; color: #555555; padding: 10px 10px 0;">
                                                    <a href={LINK_8} style="margin: 0;">{HEADLINE_8}</a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- 2 Even Columns : END -->
                </table>
                <!-- Email Body : END -->

                <!-- Email Footer : BEGIN -->
    	        <table align="center" role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="margin: auto;">
                    <tr>
                        <td style="padding: 20px; font-family: sans-serif; font-size: 12px; line-height: 15px; text-align: center; color: #000;">
                            <br><br>
    						<span class="unstyle-auto-detected-links"> Made with 🖤 in Seattle</span>
                            <br><br>
                            <a href="mailto:morningminits@gmail.com?subject=Unsubscribe me!">Unsubscribe</a>
                        </td>
                    </tr>
                </table>
                <!-- Email Footer : END -->

                <!--[if mso]>
                </td>
                </tr>
                </table>
                <![endif]-->
            </div>

        <!--[if mso | IE]>
        </td>
        </tr>
        </table>
        <![endif]-->
        </center>
    </body>
    </html>
    """

    for i in range(HEADLINE_COUNT):
        linkPlaceholder = '{LINK_' + str(i+1) + '}'
        headlinePlaceholder = '{HEADLINE_' + str(i+1) + '}'
        imagePlaceholder = '{IMAGE_' + str(i+1) + '}'
        datePlaceholder = '{DATE}'

        linkActual = str("\"" + str(articleUrls[i]) + "\"")
        imageActual = str("\"" + str(articleImages[i]) + "\"")
        headlineActual = str(articleHeadlines[i])

        html = html.replace(datePlaceholder, str((datetime.today() + timedelta(days=1)).strftime('%A %B %d')))
        html = html.replace(linkPlaceholder, linkActual)
        html = html.replace(headlinePlaceholder, headlineActual)
        html = html.replace(imagePlaceholder, imageActual)

    
    text_file = open('html.txt', 'w')
    text_file.write(html)
    text_file.close()
    
    # part1 = MIMEText(html, "html")

    # attachment = open(filename, "rb")
    # part2 = MIMEBase("application", "octet-stream")
    # part2.set_payload(attachment.read())

    # # Encode file in ASCII characters to send by email
    # encoders.encode_base64(part2)

    # # Add header as key/value pair to attachment part
    # part2.add_header(
    #     "Content-Disposition",
    #     "attachment; filename= " + filename,
    # )

    # message.attach(part1)
    # message.attach(part2)

    # print("Sending emails")

    # Create secure connection with server and send email
    # context = ssl.create_default_context()
    # with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    #     server.login(SENDER_EMAIL, password)
    #     for receiverEmail in receiverEmailList:
    #         message["To"] = receiverEmail[0]
    #         server.sendmail(
    #             SENDER_EMAIL, receiverEmail, message.as_string()
    #         )


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
       if(min == 0 and sec == 0):
              return audio

       end_time = (min*60*1000+sec*1000) * -1
       return audio[:end_time]


if __name__ == '__main__':
       main()