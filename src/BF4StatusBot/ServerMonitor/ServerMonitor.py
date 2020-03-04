#  Copyright (C) 2020. Hedius gitlab.com/hedius
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

import numpy
import pkg_resources
import json

import discord

import aiohttp
import asyncio

import logging


class ServerMonitor:
    """Shows the current map and player count of the given BF4 server
    in the bot's Discord presence
    """

    def __init__(self, bot: discord.Client):
        """Init a new object
        :param bot: discord.Client: discord Bot
        """
        self.bot = bot

        # resources
        self.resource_maps = "resources/maps.json"
        self.maps = None  # dict

        # objects
        self.lock = asyncio.Lock()
        self._cur_activity_players = None
        self._cur_activity_map = None
        self._cur_status = None

        # cache to prevent updating of name twice
        self._last_activity = None

        self.load_resources()

    def load_resources(self):
        """Load resources/maps.json to self.maps
        self.map (dict) connects the engine name of maps with
        their human-readable name
        """
        resource_package = __name__
        with pkg_resources.resource_stream(resource_package, self.resource_maps) as file:
            self.maps = json.load(file)

    def get_readable_map_name(self, engine_name: str) -> str:
        """Convert the engine name of the given map to the
        its human-readable name
        :param engine_name: string: e.g. MP_Damage
        :return: human-readable name
        """
        if engine_name in self.maps:
            return self.maps[engine_name]
        return f"unknown map: {engine_name}"

    async def get_server_status(self, session: aiohttp.ClientSession, server_guid: str):
        """Get the player count and current map of the given server
        Also saves the result in class members
        :param session: aiohttp session
        :param server_guid: guid of the BF4 server to check
        :returns: 3-tuple:
                    activity: "Watching x/y online players"
                    presence: Online: >= 60% players
                              AFK: 35% - 60% players
                              DND: < 35% players
                    activity: "Playing map_name"
        """
        url = f"http://battlelog.battlefield.com/bf4/servers/show/pc/{server_guid}/?json=1&join=false"
        async with session.get(url) as r:
            data = await r.json()
            try:
                # players
                max_slots = data["message"]["SERVER_INFO"]["slots"]["2"]["max"]
                true_player_count = len(data["message"]["SERVER_PLAYERS"])

                # map
                map_name = self.get_readable_map_name(data["message"]["SERVER_INFO"]["map"])
            except TypeError:
                logging.warning(f"Server with guid {server_guid} is offline.")
                activity = discord.Game(name="offline")
                status = discord.Status.dnd
                async with self.lock:
                    self._cur_activity_players = self._cur_activity_map = activity
                    self._cur_status = status
                return activity, discord.Status.dnd, activity

            # do not show values > max_players
            true_player_count = numpy.clip(true_player_count, 0, max_slots)

            # online
            if true_player_count / max_slots >= 0.6:
                status = discord.Status.online
            # afk
            elif true_player_count / max_slots >= 0.35:
                status = discord.Status.idle
            # dnd
            else:
                status = discord.Status.dnd
            activity_players = discord.Activity(name=f"{true_player_count}/{max_slots} online players",
                                                type=discord.ActivityType.watching)
            activity_map = discord.Game(name=map_name)
            async with self.lock:
                self._cur_activity_players = activity_players
                self._cur_activity_map = activity_map
                self._cur_status = status
            return activity_players, status, activity_map

    async def set_presence(self, activity: discord.Activity, status: discord.Status):
        """Changes the discord presence
        :param activity: discord.Activity
        :param status: discord.Status
        """
        # only change the presence if it changed
        if self._last_activity == activity.name:
            return
        self._last_activity = activity.name

        try:
            await self.bot.change_presence(activity=activity, status=status)
        except discord.InvalidArgument:
            logging.exception("Called discord.Client.change_presence with an invalid argument.")

    async def monitor(self, server_guid: str, check_map: bool = True, interval_presence_change: int = 20,
                      interval_battlelog_fetch: int = 20):
        """Monitor the given server and display the status in the bot's presence
        :param server_guid: guid of the BF4 server to monitor
        :param check_map: should the bot also show the map?
            default: True
        :param interval_presence_change: delay between presence changes in seconds
            default: 20 seconds
        :param interval_battlelog_fetch: delay between Battlelog requests
            default: 20 seconds
        """

        async def monitor_server():
            """asyncio task for fetching new data from Battlelog"""
            async with aiohttp.ClientSession() as session:
                while True:
                    # data is cached in members by self.get_server_status
                    try:
                        await self.get_server_status(session, server_guid)
                    except:  # ...
                        logging.error("Error while fetching data from Battlelog!")
                    await asyncio.sleep(interval_battlelog_fetch)

        async def set_presence():
            """asyncio task for updating the bot's discord presence"""
            while True:
                # copy data from cache
                async with self.lock:
                    activity_players = self._cur_activity_players
                    activity_map = self._cur_activity_map
                    status = self._cur_status

                # make sure that we received data from battlelog
                if None in (activity_players, activity_map, status):
                    await asyncio.sleep(10)
                    continue

                # set player count
                await self.set_presence(activity_players, status)
                await asyncio.sleep(interval_presence_change)

                # set map
                if check_map:
                    await self.set_presence(activity_map, status)
                    await asyncio.sleep(interval_presence_change)

        interval_presence_change = numpy.clip(interval_presence_change, 3, 120)

        # create asyncio tasks
        task_gatherer = asyncio.create_task(monitor_server())
        task_set_presence = asyncio.create_task(set_presence())
        await task_gatherer
        await task_set_presence
