# Carbon News

---

### Overview

The script first searches the custom google search engine and collects all urls given by the search engine. Articles are then extracted through their url by using [newscat](https://github.com/slyrz/newscat/tree/master) to get the text of the articles. We then push these text files to the agent. The agent creates their embeddings, and uses them when querying.

### Requirements

1. Python 3.9
2. OpenAI API Key

### Components

1. Custom Google Search Engine ([link](https://programmablesearchengine.google.com/))
2. newscat ([link](https://github.com/slyrz/newscat/tree/master))
3. langchain agent ([link](https://python.langchain.com/))

## Mounting EFS on EC2

---

1. `sudo yum install -y amazon-efs-utils`
2. `sudo mount -t efs -o tls fs-0123456789:/ /path/to/mnt`

## Deploying to EC2 (Slack Bot)

---

1. ssh into ec2
2. scp `app.py` into ec2
3. make sure you have golang installed
4. install the required packages
    1. for the app: `pip install langchain openai chromadb tiktoken google-api-python-client`
    2. for deploying fastapi: `pip install fastapi uvicorn pickle5 pydantic requests pypi-json pyngrok nest-asyncio python-multipart httpx`
    3. you might encounter a problem with chromadb (see below)
5. install newscat
    1. `go install github.com/slyrz/newscat@latest`
    2. add GOPATH to your PATH
    
    ```bash
    export GOPATH=$HOME/go
    export PATH=$PATH:$GOROOT/bin:$GOPATH/bin
    ```
    
6. run `python app.py 1 1`
    1. the 2 positional arguments determine if the script will search for articles and extract links respectively. set them to 0 or omit them if you want to skip those steps.
7. to start a running process
    1. start a screen session with `screen`
    2. run `python app.py`
    3. press `ctrl + a`, followed by `d` to leave it in the background
8. if you want to go back to a running session, do `screen -r` or alternatively, to check the session pid, `ps aux | grep screen`
    1. to kill, do `kill -15 [pid]`

### Possible problems you might encounter

- chromadb — `RuntimeError: Unsupported compiler -- at least C++11 support is needed!`
    - you need g++, run the following commands and try again
    - `sudo yum -y install gcc`
    - `sudo yum -y install gcc-c++`
    - `sudo yum install python3-devel`

### Systemd

```bash
[Unit]
Description=carbon news service

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=1

[Install]
WantedBy=multi-user.target
```
