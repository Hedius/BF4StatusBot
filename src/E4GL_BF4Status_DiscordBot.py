#!/usr/bin/env python3
"""
Copyright (C) 2019 Hedius gitlab.com/hedius

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
__author__ = "Hedius"
__version__ = "1.0"
__license__ = "GPLv3"
__status__ = "Production"

import sys
import os
import configparser
import argparse

import asyncio
import logging

import aiohttp
import discord


class LivePlayercountBot(discord.Client):
    """Discord bot to display the BL true playercount in the bot status"""
    async def on_ready(self):
        logging.info(f"Logged on as {self.user}")
        status = ""
        async with aiohttp.ClientSession() as session:
            while True:
                newstatus = (await get_playercount(session)) + " players online"
                if newstatus != status:
                    await self.change_presence(activity=discord.Game(newstatus))
                    status = newstatus
                await asyncio.sleep(10)


async def get_playercount(session):
    """Get the current playerdata from BL"""
    try:
        url = f"http://battlelog.battlefield.com/bf4/servers/show/pc/{SERVER_GUID}/?json=1&join=false"
        async with session.get(url) as r:
            page = await r.json()
            max_slots = page["message"]["SERVER_INFO"]["slots"]["2"]["max"]
            true_playercount = len(page["message"]["SERVER_PLAYERS"])
            true_playercount = (max_slots) if true_playercount >= max_slots else true_playercount
            return f"{true_playercount}/{max_slots}"
    except Exception:
        logging.exception("Error getting data from battlelog")  # BL autism


# Config/Argv
def readConfig(configFile):
    """reads the config
    :param configFile: path to config file
    :returns: bot secret, server guid
    """
    # read config
    if not os.path.isfile(configFile):
        print("Error while accessing config!", file=sys.stderr)
        exit(1)

    config = configparser.ConfigParser(interpolation=None)
    config.read(configFile)
    # data
    try:
        section = config["BOT"]
        token = section["BOT_TOKEN"]
        guid = section["SERVER_GUID"]
    except (configparser.Error, KeyError):
        print("Error while reading config!",
              file=sys.stderr)
        exit(1)
    return token, guid


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s]: %(message)s"
    )
    global BOT_TOKEN
    global SERVER_GUID

    parser = argparse.ArgumentParser(description="Discord Bot for displaying"
                                     "status of BF4 servers by E4GL")
    parser.add_argument("-c", "--config", help="path to config file",
                        required=True, dest="configFile")
    args = parser.parse_args()

    BOT_TOKEN, SERVER_GUID = readConfig(args.configFile)

    LivePlayercountBot().run(BOT_TOKEN)


if __name__ == "__main__":
    main()
