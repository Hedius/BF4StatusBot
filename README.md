# E4GL BF4 Status Discord Bot
This discord bot allows you to display the player count of your BF4 servers on discord.
 Furthermore, the bot also displays the current map and changes its status according to the current population (Online, AFK, DND).

![Player Count](https://i.imgur.com/nkDYLh7.png "Player Count")
![Current Map](https://imgur.com/tQ2HCAN.png "Current Map")

This project is  a fork of Potato's bot.

The bot may be run within a container, in a venv, or directly on a host.


# Setup
## 1. docker (docker-compose)
 1. clone the repository
 2. adjust docker-compose.yml with your settings
    (**See chapter: Configuration**)
    - `vim docker-compose.yml`
        * bot token and server guid are needed
    - create an own service for each bot in the docker-compe.yml
 3. sudo docker-compose up -d
 
## 2. venv/host
The bot is not daemonized.
 
1. You only need the folder **src**.
2. (**optional**) switch to a venv
3. Install dependencies
   ```
   cd src
   pip3 install --user -r requirements.txt
   ```
4. Edit the configuration or set environment variables
   (**See chapter: Configuration**)

5. Run the bot with ``python3 src/run.py``
  
 
# Updating
## docker-compose
1. sudo docker-compose down --rmi all
2. git pull
3. sudo docker-compose up -d

 
# Configuration
## 1. Environment variables
### Required
- BF4STATUSBOT_BOT_TOKEN
    - Discord Bot Token
- BF4STATUSBOT_SERVER_GUID
    - GUID of the bf4 server.
    
 ### Optional
The following values are default and will be used if not set:
- BF4STATUSBOT_CHECK_MAP=true
    - Boolean
    - Should the bot also display the current map?
- BF4STATUSBOT_INTERVAL_PRESENCE_CHANGE=5
    - seconds (int)
    - The interval for presence changes.
- BF4STATUSBOT_INTERVAL_BATTLELOG_FETCH=20
    - seconds (int)
    - The interval for sending requests to Battlelog.
    
## 2. Toml files
You can also use configuration files.
# Docker
Each bot requires its own config.

Possibilities:
1. Bind config directory
    1. Bind the container directory ``/usr/src/app/config`` to your docker host.
    2. Modify ``default.toml`` or copy ``user.toml.example`` to ``user.toml``.
2. Bind config file
    1. Copy the file ``cp src/config/user.toml.example server_1.toml``.
    2. Bind the file to ``/usr/src/app/config/user.toml`` 

# License
This project is free software and licensed under the GPLv3.
