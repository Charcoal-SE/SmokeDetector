SmokeDetector
=============

[![Build Status](https://travis-ci.org/Charcoal-SE/SmokeDetector.svg?branch=master)](https://travis-ci.org/Charcoal-SE/SmokeDetector)
[![Circle CI](https://circleci.com/gh/Charcoal-SE/SmokeDetector.svg?style=shield)](https://circleci.com/gh/Charcoal-SE/SmokeDetector)
[![Coverage Status](https://coveralls.io/repos/github/Charcoal-SE/SmokeDetector/badge.svg?branch=master)](https://coveralls.io/github/Charcoal-SE/SmokeDetector?branch=master)
[![Open issues](https://img.shields.io/github/issues/Charcoal-SE/SmokeDetector.svg)](https://github.com/Charcoal-SE/SmokeDetector/issues)
[![Open PRs](https://img.shields.io/github/issues-pr/Charcoal-SE/SmokeDetector.svg)](https://github.com/Charcoal-SE/SmokeDetector/pulls)


Headless chatbot that detects spam and posts it to chatrooms.
Uses [ChatExchange](https://github.com/Manishearth/ChatExchange),
takes questions from the Stack Exchange
[realtime tab](https://stackexchange.com/questions?tab=realtime),
and accesses answers via the [Stack Exchange API](https://api.stackexchange.com/).

Example [chat post](https://chat.stackexchange.com/transcript/message/43579469):

![Example chat post](https://i.stack.imgur.com/oLyfb.png)

## 문서화

사용자를 위한 문서는 위키를 참조하십시오. [wiki](https://charcoal-se.org/smokey).

SmokeDetector를 설정하고 실행시키기 위한 자세한 정보는 아래 링크를 참조하십시오.
[setting up and running SmokeDetector is in the wiki](https://charcoal-se.org/smokey/Set-Up-and-Run-SmokeDetector).

### 기본 설정

SmokeDetector를 설정하기 위해서는, 아래의 명령어를 사용하십시오.

```shell
git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector
git checkout deploy
sudo pip3 install -r requirements.txt --upgrade
pip3 install --user -r user_requirements.txt --upgrade
```

그 다음, `config.sample` 를 `config`라는 이름의 새로운 파일로 복사합니다.
필요한 값들을 수정합니다.

실행을 위해서는 `python3 nocrash.py`를 사용하십시오.
(preferably in a daemon-able mode, like a `screen` session.)
당신은 `python3 ws.py`또한 사용하실 수 있습니다.,
그러나 SmokeDetector는 6시간 후에 작동이 중지될 것입니다;
`nocrash.py`에서 실행되고 있다면, 재시작 될것입니다.
(This is to be sure that closed websockets, if any, are reopened.)

### 가상 환경 설정

가상환경에서 구동시키는것 [virtual environment](https://docs.python.org/3/tutorial/venv.html)
은 당신의 local system에서 패키지를 isolate 시키는데 좋은 방법입니다.
SmokeDetector를 가상환경에서 설정하고 싶다면, 아래 명령어를 사용하십시오.

```shell
git clone https://github.com/Charcoal-SE/SmokeDetector.git
cd SmokeDetector
git config user.email "smokey@erwaysoftware.com"
git config user.name "SmokeDetector"
git checkout deploy

python3 -m venv env
env/bin/pip3 install -r requirements.txt --upgrade
env/bin/pip3 install --user -r user_requirements.txt --upgrade
```

그 다음, config 파일을 복사하고 위에 언급한대로 수정하십시오.
SmokeDetector를 이 가상환경에서 구동시키려면, 아래의 명령어를 사용하십시오.
`env/bin/python3 nocrash.py`.

### Docker 설정

[Docker container](https://www.docker.com/resources/what-container)
에서 실행하는 것은 당신의 local system에서 패키지들을 isolate 시키는 더 좋은 방법이 될 수 있습니다.
SmokeDetector를 Docker container에서 설정하고 싶다면, 아래의 단계를 따르십시오.

1. 파일을 Grab 한 후 [Dockerfile](Dockerfile) SmokeDetector의 이미지를 빌드하십시오.:

  ```shell
  DATE=$(date +%F)
  mkdir temp
  cd temp
  wget https://raw.githubusercontent.com/Charcoal-SE/SmokeDetector/master/Dockerfile
  docker build -t smokey:$DATE .
  ```

2. 당신이 만든 container 로 부터 이미지를 만드십시오.

  ```shell
  docker create --name=mysmokedetector smokedetector:$DATE
  ```

3. container를 실행시키십시오..
  걱정하지 마세요, SmokeDetector는 준비되기 전까지 실행되지 않을것이기 때문에,
  SmokeDetector가 실행되기 전에 설정 파일을 수정할 기회가 남아있습니다.

  `config.sample`를 `config`라는 이름의 새로운 파일로 복사합니다.
  그리고 필요한 값들을 수정할 수 있습니다. 
  그 다음, 아래의 명령어를 통해 container를 파일로 복사할 수 있습니다:

  ```shell
  docker cp config mysmokedetector:/home/smokey/SmokeDetector/config
  ```

4. 만약 당신이 부가적인 것들 (SSH, Git etc.) 를 설정하고 싶다면,
  container안의 Bash shell을 가지고 그것들을 할 수 있습니다:

  ```shell
  docker exec -it mysmokedetector bash
  ```

  준비가 다 되었다면, `ready`라는 이름의 파일을 `/home/smokey`경로 아래에 위치하십시오:

  ```shell
  touch ~smokey/ready
  ```

#### Automate Docker를 Docker Compose로 전개하는 방법

당신은 아마 Docker 와 Docker Compose에 대한 기본적인 개념들을 가지고 있을 것이다.

당신이 할 첫 번째로 해야할 것은 `config`파일을 적절하게 채우는 것이다.
[the sample](config.sample)을 참조하십시오.

폴더를 상성하십시오. (당신이 원하는 대로 이름지어도 됩니다.),
`config` 파일과 [`docker-compose.yml` file](docker-compose.yml) 를 위치시키십시오.
`docker-compose up -d` 를 실행시키면, 당신의 SmokeDetector instance 은 실행될 것이다.

메모리와 CPU constraint 같은 부가적인 조작을 원한다면,
`docker-compose.yml` 를 수정하거나 `smokey` keys 를 참조하십시오.
예시의 값들은 권장되는 값들입니다.

```yaml
restart: always  # when your host reboots Smokey can autostart
mem_limit: 512M
cpus: 0.5  # Recommend 2.0 or more for spam waves
```

## Requirements

SmokeDetector 는 Stack Exchange logins 만을 지원하고,
Python 3.5 나 그 상위 버전에서 작동합니다.

To allow committing blacklist and watchlist modifications
back to GitHub,
your system also needs Git 1.8 or higher,
although we recommend Git 2.11+.

## License

Licensed under either of

 * Apache License, Version 2.0, ([LICENSE-APACHE](LICENSE-APACHE)
   or http://www.apache.org/licenses/LICENSE-2.0)
 * MIT license ([LICENSE-MIT](LICENSE-MIT)
   or http://opensource.org/licenses/MIT)

at your option.

### Contribution Licensing

By submitting your contribution for inclusion in the work
as defined in the [Apache-2.0 license](https://www.apache.org/licenses/LICENSE-2.0),
you agree that it be dual licensed as above,
without any additional terms or conditions. 
