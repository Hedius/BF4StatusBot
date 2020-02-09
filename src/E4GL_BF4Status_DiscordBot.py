#!/usr/bin/env python3

__author__ = "Hedius"
__version__ = "1.0.0"
__license__ = "GPLv3"

#  Copyright (C) 2020. Hedius gitlab.com/hedius
#  Copyright (C) 2020. Potato for the example
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import configparser
import argparse

import asyncio
import logging

import aiohttp
import discord


class BF4StatusBot(discord.Client):
    """Discord bot to display the true playercount as a bot status"""

    def __init__(self, server_guid: str):
        super().__init__()
        self.server_guid = server_guid

    async def on_ready(self):
        status = ""
        async with aiohttp.ClientSession() as session:
            while True:
                new_status, presence_status = await self.get_playercount(session)
                if new_status != status:
                    await self.change_presence(activity=discord.Game(new_status),
                                               status=presence_status)
                    status = new_status
                await asyncio.sleep(30)

    async def get_playercount(self, session):
        """Return the current content for the given presence
        :param session: aoihttp session
        :return: status, and presence_status (Online, AFK, DND)
        """
        try:
            url = f"http://battlelog.battlefield.com/bf4/servers/show/pc/{self.server_guid}/?json=1&join=false"
            async with session.get(url) as r:
                page = await r.json()
                try:
                    max_slots = page["message"]["SERVER_INFO"]["slots"]["2"]["max"]
                    true_playercount = len(page["message"]["SERVER_PLAYERS"])
                except TypeError:
                    logging.exception("Server offline")
                    return f"offline", discord.Status.dnd

                true_playercount = max_slots if true_playercount >= max_slots else true_playercount

                if true_playercount / max_slots >= 0.6:
                    status = discord.Status.online
                elif true_playercount / max_slots >= 0.35:
                    status = discord.Status.idle
                else:
                    status = discord.Status.dnd
                return f"{true_playercount}/{max_slots} players online", status
        except Exception:
            logging.exception("Error getting data from battlelog")


# Config/Argv
def read_config(config_file):
    """Read the config
    :param config_file: path to config file
    :return: bot secret, server guid
    """
    # read config
    if not os.path.isfile(config_file):
        print("Error while accessing config!", file=sys.stderr)
        exit(1)

    config = configparser.ConfigParser(interpolation=None)
    config.read(config_file)
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

    parser = argparse.ArgumentParser(description="Discord bot for displaying"
                                                 "the status of BF4 servers on Discord")
    parser.add_argument("-c", "--config", help="path to config file",
                        required=True, dest="configFile")
    args = parser.parse_args()

    bot_token, server_guid = read_config(args.configFile)

    BF4StatusBot(server_guid).run(bot_token)


if __name__ == "__main__":
    main()
