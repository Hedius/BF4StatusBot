# E4GL BF4 Status Discord Bot
This docker image allows you to display the player count of your  BF4 servers on discord.

This image extends Potato's original discord bot.

## Installation
### docker-compose
 1. clone the repository
 2. adjust the config - Repeat the following steps for each server
    1. `cp discordbot.cfg.example discordbot_server1.cfg`
    2. edit the config
        * bot token and server guid needed
    3. create a own service for each bot in the docker-compe.yml:w
 3. sudo docker-compose up -d

## Updating
### docker-compose
 1. sudo docker-compose down --rmi all
 2. git pull
 3. sudo docker-compose up -d
