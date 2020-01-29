import sys
import smtplib, ssl
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase

senderEmail = "morningminits@gmail.com"
receiverEmailList = ["karthikravi97@gmail.com", "sfeizi97@gmail.com", "shikardhar12345@gmail.com", "skunal8197@gmail.com", "sidvashist@gmail.com", "kishora1997@gmail.com"]
password = input("Enter password for morningminits@gmail.com:")

subject = "Morning Minits"

message = MIMEMultipart("alternative")
message["Subject"] = subject
message["From"] = senderEmail

html = """\
<html>
  <body>
    <p>
        Hope you enjoyed the Morning Minits! You can find the links to the articles referenced in the minits below for further reading. <br>
        <br>
        <a href-={LINK_1} > {HEADLINE_1} </a> <br>
        <a href-={LINK_2} > {HEADLINE_2} </a> <br>
        <a href-={LINK_3} > {HEADLINE_3} </a> <br>
        <a href-={LINK_4} > {HEADLINE_4} </a> <br>
        <a href-={LINK_5} > {HEADLINE_5} </a> <br>
        <a href-={LINK_6} > {HEADLINE_6} </a> <br>
        <a href-={LINK_7} > {HEADLINE_7} </a> <br>
        <a href-={LINK_8} > {HEADLINE_8} </a> <br>
        <a href-={LINK_9} > {HEADLINE_9} </a> <br>
        <a href-={LINK_10} > {HEADLINE_10} </a> <br>

    </p>
  </body>
</html>
"""


part1 = MIMEText(html, "html")

filename = "index.html"  # In same directory as script

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

# Create secure connection with server and send email
context = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
    server.login(senderEmail, password)
    for receiverEmail in receiverEmailList:
        message["To"] = receiverEmail
        server.sendmail(
            senderEmail, receiverEmail, message.as_string()
        )
