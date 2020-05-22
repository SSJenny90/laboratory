from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import smtplib
from laboratory import config
import os 

MESSAGES = dict(
    error = 'I\'ve got some bad news! The {} is no longer sending or receiving messages so I\'m going to shut down the lab until you can come take a look.',
    delayed_start = 'It just ticked over to {} so I\'m going to set up the instruments and get things underway.',
    success = "Just letting you know that step {} is now complete! I\'m going to set the temperature to {}C and get started on step {}.\n\nEstimated completion time for step {} is: {}.\n",
)

def send_email(message,cc=False,logfile=False,data=None, args=[]):
    """Sends an email to the specified email address. logfile or datafile can
    be attached if desired. used mainly for email updates on progress during
    long measurement cycles. mailer is geophysicslabnotifications@gmail.com.

    :param toaddr: full email address of intended recipient
    :type toaddr: str

    :param message: message to include in email
    :type message: str

    :param cc: email can be carbon copied to additional adresses in cc
    :type cc: str,list

    :param logfile: whether to attach the current logfile
    :type logfile: boolean

    :param datafile: whether to attach the current datafile
    :type datafile: boolean
    """
    if not config.EMAIL:
        return

    message = MESSAGES.get(message, message).format(*args)
    fromaddr = config.EMAIL['from']
    toaddr = config.EMAIL['to']
    try:
        msg = MIMEMultipart()
        msg['From'] = fromaddr
        msg['To'] = toaddr
        
        if cc:
            msg['Cc'] = cc
        msg['Subject'] = "Lab Notification"
        body = 'Hi,\n\n{}'.format(message)
        body += '\n\nCheers,\nYour Friendly Lab Assistant' 
        msg.attach(MIMEText(body, 'plain'))

        if logfile:
            part = MIMEBase('application', "octet-stream")
            part.set_payload(open(logfile, "rb").read())
            part.add_header('Content-Disposition', 'attachment', filename='controlLog.txt')
            msg.attach(part)

        if data is not None:
            part = MIMEBase('application', "octet-stream")
            part.set_payload(data.to_csv().encode())
            part.add_header('Content-Disposition', 'attachment', filename='data.csv')
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.connect("smtp.gmail.com",587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(fromaddr, config.EMAIL['pw'])
        text = msg.as_string()
        if cc:
            server.sendmail(fromaddr, [toaddr,cc], text)
        else:
            server.sendmail(fromaddr, toaddr, text)
        server.quit
    except Exception:
        pass




