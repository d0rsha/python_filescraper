# Python fileparser 
Search directory for filename.  
Search matched files line by line for regEx pattern.  
Adds matched patterns to dictionary.  


```bash
## Parallel and multithreaded script 
python3 mainParser.py <bucketName>

## Single process and single threaded script 
python pythonParser.py <bucketname>
```

# mutt setup
Needs to be setup locally, can send email with testresults attached 
```text
 set imap_user = "YOUR_EMAIL@hotmail.com"
 set imap_pass = "YOUR_PASSWORD"
 set smtp_url = "smtp://YOUR_EMAIL@hotmail.com@smtp.live.com:587/"
 set smtp_pass = "YOUR_PASSWORD"
 set from = "YOUR_EMAIL@hotmail.com"
 set realname = "FIRST LAST"
 set ssl_force_tls = yes
 ```