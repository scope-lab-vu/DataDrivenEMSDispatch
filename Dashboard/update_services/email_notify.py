import smtplib
import sys
import configparser

###############################################
# Constants 

CONFIG_FILE = "/home/vol-gpettet/analytics-dashboard/update_services/ingest_config.cfg"
config = configparser.ConfigParser()
config.read(CONFIG_FILE)

TO = str(config['EMAIL']['to'])
#SUBJECT = 'FD SERVER: Service Failed'
#TEXT = 'Here is a message from python.'

# Gmail Sign In
GMAIL_SENDER = str(config['EMAIL']['gmail_sender'])
GMAIL_PASSWORD = str(config['EMAIL']['gmail_password'])


def send_email_alert(subject, text):

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(GMAIL_SENDER, GMAIL_PASSWORD)

    BODY = '\r\n'.join(['To: %s' % TO,
                        'From: %s' % GMAIL_SENDER,
                        'Subject: %s' % subject,
                        '', text])

    try:
        server.sendmail(GMAIL_SENDER, [TO], BODY)
        print ('email sent')
    except:
        print ('error sending mail')

    server.quit()


#print(len(sys.argv))
#print(str(sys.argv))
send_email_alert(sys.argv[1], sys.argv[2])

