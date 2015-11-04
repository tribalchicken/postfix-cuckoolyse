#!/usr/bin/python
## Cuckoolyse-filter. Do not use without some effort!
## Extract attachments from email and submit to remote cuckoo instance, then reinject back to queue
## Initial goal was a postfix simple content filter.
##
## Author: Thomas White <thomas@tribalchicken.com.au>
## https://tribalchicken.com.au
#
# Suggest you do not use this without some work!!!

# TODO: Probably needs a sanity check on the file size

import email
import smtplib
import sys
import magic
import requests
import subprocess
import logging

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s',filename='/home/cuckoolyse/cuckoolyse.log',filemode='a')

### CONFIG OPTIONS ###
# MIME Types to extract and submit from the email
mtypes = [
            'application/octet-stream',
            'application/msword',
            'application/pdf',
            'application/x-msdownload',
            'application/javascript',
            'application/x-rar-compressed'
         ]

#REST URL for Cuckoo submission
url = "http://YOUR_CUCKOO_URL:8090/tasks/create/file"

# Bypass on submission failure - Highly recommend to set to True. False will return a temporary failure if we can't submit to cuckoo
# Probably doesn't really have a use if we are not making decisions based on Cuckoo
failureBypass = True

# Reinjection method - sendmail or smtplib
# smtplib allows submission to an alternate port, for example submission straight to amavis
# sendmail will simply reinject back into the postfix queue
injectMethod = 'smtplib'

## smtplib options
smtpHost = 'localhost'
smtpPort = 10024 # Amavis instance

## Sendmail options

# Submit the sample to cuckoo and get a result
# TODO: No results yet, just submit and pass back to Postfix
# Returns true if allowed to pass, or false to reject
def cuckoolyse(msg):
    # Check if multipart
    if not msg.is_multipart():
        #Not multipart? Then we don't care, pass it back
        logging.debug("Returning non-multipart message to queue.")
        return True

    # Cycle through multipart message
    # Find attachments (application/octet-stream?)
    for part in msg.walk():
        # TODO: Other mime types? pdf? doc?
        logging.debug("Processing mail part of type %s" % (part.get_content_type()))
        if part.get_content_type().strip() in mtypes:
            # Extract attachment to a staging directory
            # Extract attachment to memory?
            attachment = part.get_payload(decode=True)
            mtype = magic.from_buffer(attachment, mime=True)
            if mtype not in mtypes:
                return

            logging.info("Found attachment %s of type %s from %s" %(part.get_filename(), mtype, msg['from']))

            files = dict(
                file = attachment,
                filename = part.get_filename()
            )

            data = dict(
                package="",
                timeout=0,
                options="",
                priority=1,
                machine="",
                platform="",
                memory=False,
                enforce_timeout=False,
               custom="",
                tags = None
            )
            try:
                logging.info("Submitting to cuckoo via %s" % (url))
                response = requests.post(url, files=files, data=data)
                json = response.json()
                logging.debug("Received JSON response: %s" % (json))
                task_id = json["task_id"]
                if task_id is None:
                    raise Exception("Cuckoo did not response with a Task ID. Assuming submission failure")
                logging.info("SUCCESS: Submitted to remote Cuckoo instance as task ID %i" % (task_id))
                return True
            except Exception as e:
                logging.error("Unable to submit file to Cuckoo: %s" %(e))
                return failureBypass #NOTE: If false, this will fail hard and bounce the mail!!

def reinject(msg):
    msgFrom = msg['From']
    msgTo = msg['To']

    if injectMethod == 'sendmail':
        smCommand = ["/usr/sbin/sendmail", "-G", "-i", msgTo]
        retval = 0
        stdout = ''
        stderr = ''
        try :
            process = subprocess.Popen(smCommand, stdin=subprocess.PIPE)
            (stdout, stderr) = process.communicate(msg.as_string());
            retval = process.wait()
            logging.info("Reinjected via sendmail.")
            sys.exit(0)
        except Exception, e:
            print str(e)
            logging.error("Sendmail failed: %s" % (e))
            sys.exit(75)
    if injectMethod == 'smtplib':
        try:
            smtpObj = smtplib.SMTP(smtpHost, smtpPort)
            smtpObj.sendmail(msgFrom,msgTo,msg.as_string())
            logging.info("Message reinjected via SMTP.")
        except Exception, e:
            print str(e)
            sys.exit(75)



input = sys.stdin.readlines()
msg = email.message_from_string(''.join(input))
cuckoolyse(msg)
#if cuckoolyse(msg) is True:
#    reinject(msg)
#else:
#    pass
