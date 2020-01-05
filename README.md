# E4GL BF4Status Discord Bot
This docker image allows you to display the player count of your  BF4 servers on discord.

## Installation
### docker-compose
 1. clone the repository
 2. copy discordbot.cfg.example to discordbot.cfg and edit it
 3. sudo docker-compose up -d

## Updating
### docker-compose
 1. sudo docker-compose down --rmi all
 2. git pull
 3. sudo docker-compose up -d
