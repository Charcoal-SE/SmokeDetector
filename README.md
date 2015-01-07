SmokeDetector [![Build Status](https://travis-ci.org/Charcoal-SE/SmokeDetector.svg?branch=master)](https://travis-ci.org/Charcoal-SE/SmokeDetector)
=============

Headless chatbot that detects spam and posts it to chatrooms. Uses [ChatExchange](https://github.com/Manishearth/ChatExchange) and takes questions from the Stack Exchange [realtime tab](http://stackexchange.com/questions?tab=realtime).

Example [chat post](http://chat.stackexchange.com/transcript/11540?m=17962164#17962164):

![Example chat post](http://i.stack.imgur.com/d8pbW.png)

To set up, use

```
git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector
git submodule init
git submodule update
sudo pip install beautifulsoup4
sudo pip install requests --upgrade
sudo pip install websocket-client --upgrade
sudo pip install phonenumbers
```

To run, use `python ws.py` (preferably in a daemon-able mode). Like in a `screen` session.


You can run `. ChatExchange/setup.sh` to set local environment variables so that you don't have to log in every time. 

Only supports Stack Exchange OpenIDs for now.
