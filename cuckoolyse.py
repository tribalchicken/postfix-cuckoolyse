#!/usr/bin/python
## Cuckoolyse
## Extract attachments from email and submit to remote cuckoo instance
## Initially a Postfix filter, but can be used with any email message Python is happy with.
##
## Author: Thomas White <thomas@tribalchicken.com.au>
## https://tribalchicken.com.au


# TODO: Configurable logging location
# TODO: Probably needs a sanity check on the file size
# TODO: Write out to staging file rather than keeping object in-memory? Maybe?

import email
import sys
import magic
import requests
import logging
import hashlib

logging.basicConfig(level=logging.DEBUG,format='%(asctime)s %(levelname)s %(message)s',filename='/tmp/cuckoolyse.log',filemode='a')

### CONFIG OPTIONS ###
# MIME Types to extract and submit from the email
mtypes = [
            'application/octet-stream',
            'application/msword',
            'application/pdf',
            'application/x-msdownload',
            'application/zip',
            'application/javascript',
            'application/x-rar-compressed'
            'text/javascript',
            'application/x-compressed',
         ]

#REST URL for Cuckoo submission
url = "http://YOUR_CUCKOO_ADDR:8090"

# Prefix to prepend to filename in submission
prefix = "AUTOSUBMIT-"

# Submit the sample to cuckoo
def cuckoolyse(msg):
    # Check if multipart
    if not msg.is_multipart():
        #Not multipart? Then we don't care, pass it back
        logging.debug("Returning non-multipart message to queue.")
        return

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

            # Secondary check using magic numbers
            # Sometimes we get octet-streams which we do not want to analyse
            if mtype not in mtypes:
                return

            logging.info("Found attachment %s of type %s from %s" %(part.get_filename(), mtype, msg['from']))

            # Multipart POST for Cuckoo API
            files = {"file":(prefix +part.get_filename(), attachment)}

            # May wish to set some cuckoo options?
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
		hash = hashlib.sha256()
		hash.update(attachment)
		shasum = hash.hexdigest()
                logging.info("Checking if %s has already been analysed..." % (shasum))
		
		# Request file info from Cuckoo
		response = requests.get("%s/files/view/sha256/%s" % (url,shasum))
		# 404 Response indicates hash does not exist
		# 200 indicates file already exists
		if response.status_code() == 200:
		    finfo = response.json()
		    logging.info("File has already been analysed, not submitting ()")
		elif response.status_code() == 404:
		                

                    logging.info("Submitting to cuckoo via %s" % (url))
                    # Send request
                    response = requests.post("%s/tasks/create/file" % (url), files=files, data=data)
                    json = response.json()
                    logging.debug("Received JSON response: %s" % (json))

                    # Task ID from Cuckoo
                    task_id = json["task_id"]

                    if task_id is None:
                        raise Exception("Cuckoo did not response with a Task ID. Assuming submission failure")
                    logging.info("SUCCESS: Submitted to remote Cuckoo instance as task ID %i" % (task_id))
                    return 0
		else:
		    raise Exception("Unexpected reponse code whilst requesting file details")

            except Exception as e:
                logging.error("Unable to submit file to Cuckoo: %s" %(e))
                return 1

# Get email from STDIN
input = sys.stdin.readlines()
msg = email.message_from_string(''.join(input))

# Cuckoolyse!
cuckoolyse(msg)
