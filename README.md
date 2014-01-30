SmokeDetector
=============

Headless chatbot that detects spam and posts it to chatrooms. Uses [ChatExchange](https://github.com/Manishearth/ChatExchange) and takes questions from the [realtime tab](http://stackexchange.com/questions?tab=realtime)


To setup:

```
git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector
git submodule init
git submodule update
sudo pip install beautifulsoup
sudo pip install requests --upgrade
```

To run: `python ws.py`, preferably in a daemon-able mode. Like in a `screen` session.
