SmokeDetector
=============

[![Build Status](https://travis-ci.org/Charcoal-SE/SmokeDetector.svg?branch=master)](https://travis-ci.org/Charcoal-SE/SmokeDetector) [![Circle CI](https://circleci.com/gh/Charcoal-SE/SmokeDetector.svg?style=shield)](https://circleci.com/gh/Charcoal-SE/SmokeDetector) [![Coverage Status](https://coveralls.io/repos/github/Charcoal-SE/SmokeDetector/badge.svg?branch=master)](https://coveralls.io/github/Charcoal-SE/SmokeDetector?branch=master) [![Open issues](https://img.shields.io/github/issues/Charcoal-SE/SmokeDetector.svg)](https://github.com/Charcoal-SE/SmokeDetector/issues) [![Open PRs](https://img.shields.io/github/issues-pr/Charcoal-SE/SmokeDetector.svg)](https://github.com/Charcoal-SE/SmokeDetector/pulls)


Headless chatbot that detects spam and posts it to chatrooms. Uses [ChatExchange](https://github.com/Manishearth/ChatExchange), takes questions from the Stack Exchange [realtime tab](https://stackexchange.com/questions?tab=realtime), and accesses answers via the [Stack Exchange API](https://api.stackexchange.com/).

Example [chat post](https://chat.stackexchange.com/transcript/11540?m=17962164#17962164):

![Example chat post](https://i.stack.imgur.com/oLyfb.png)

User documentation is in the [wiki](https://charcoal-se.org/smokey).

To set up, use

```
git config user.email "smokey@erwaysoftware.com"
git config user.name "SmokeDetector"

git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector
git checkout deploy
sudo pip3 install -r requirements.txt --upgrade
pip3 install --user -r user_requirements.txt --upgrade
```

Next, copy `config.sample` to a new file called `config`, and edit the values required.

To run, use `python3 nocrash.py` (preferably in a daemon-able mode, like a `screen` session.)
You can also use `python3 ws.py`, but then SmokeDetector will be shut down after 6 hours;
when running from `nocrash.py`, it will be restarted.
(This is to be sure that closed websockets, if any, are reopened.)

SmokeDetector only supports Stack Exchange logins,
and runs on Python 3.5 or higher,
for now.

## License

Licensed under either of

 * Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE) or http://www.apache.org/licenses/LICENSE-2.0)
 * MIT license ([LICENSE-MIT](LICENSE-MIT) or http://opensource.org/licenses/MIT)

at your option.

### Contribution Licensing

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in the work by you, as defined in the Apache-2.0 license, shall be dual licensed as above, without any additional terms or conditions. 

