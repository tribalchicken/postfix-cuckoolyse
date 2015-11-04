# postfix-cuckoolyse

Article with a better explanation here:

This is a simple script used with Postfix to grab email from a Pipe, scan for interesting attachments and automatically submit the attachment to Cuckoo.

It says Postfix, but will now it just takes input from a pipe really has nothing to do with postfix.

There are two versions:

- cuckoolyse: This is what I am using currently which takes email and simply submits. I use this in conjunction with Postfix's bcc_recipient_maps and recipient_transport to get a copy of all incoming mail and submit
- cuckoolyse-filter: This is the original version I wrote with the intention of using as a simple content filter. This will need some work.

Note: I do not pretend to be a coder!

Feedback and changes are welcome.
