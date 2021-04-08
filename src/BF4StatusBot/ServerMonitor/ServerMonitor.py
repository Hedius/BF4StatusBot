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
from typing import Optional

import numpy
import pkg_resources
import json

import discord

import aiohttp
import asyncio

import logging


class ServerMonitor:
    """
    Shows the current map and player count of the given BF4 server
    in the bot's Discord presence
    """

    def __init__(self, bot: discord.Client):
        """Init a new object
        :param bot: discord.Client: discord Bot
        """
        self.bot = bot

        # resources
        self.resource_maps = 'resources/maps.json'
        self.maps = None  # dict

        # objects
        self.lock = asyncio.Lock()
        self._cur_activity_players = None
        self._cur_activity_map = None
        self._cur_status = None

        # cache to prevent updating of name twice
        self._last_activity = None

        self._last_player_count = None

        self.load_resources()

    def load_resources(self):
        """
        Load resources/maps.json to self.maps
        self.map (dict) connects the engine name of maps with
        their human-readable name
        """
        resource_package = __name__
        with pkg_resources.resource_stream(resource_package,
                                           self.resource_maps) as file:
            self.maps = json.load(file)

    def get_readable_map_name(self, engine_name: str) -> str:
        """
        Convert the engine name of the given map to the
        its human-readable name
        :param engine_name: string: e.g. MP_Damage
        :return: human-readable name
        """
        if engine_name in self.maps:
            return self.maps[engine_name]
        return f'unknown map: {engine_name}'

    async def get_server_status(self, session: aiohttp.ClientSession,
                                server_guid: str) -> Optional[int]:
        """
        Get the player count and current map of the given server
        Also saves the result in class members
            activity: "Watching x/y online players"
            presence: Online: >= 60% players
                      AFK: 35% - 60% players
                      DND: < 35% players
            activity: "Playing map_name"

        :param session: aiohttp session
        :param server_guid: guid of the BF4 server to check
        :returns: the current player count. (None if the server is offline)
        """
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip,deflate'
        }
        url_keeper = f'https://keeper.battlelog.com/snapshot/{server_guid}'
        url_map = ('http://battlelog.battlefield.com/bf4/servers/'
                   f'show/pc/{server_guid}?json=1&join=false')
        try:
            async with session.get(url_keeper, headers=headers) as r:
                data = await r.json()
                snapshot = data['snapshot']
                # players
                max_slots = snapshot['maxPlayers']
                queue = snapshot['waitingPlayers']

                player_count = 0
                for team in snapshot['teamInfo']:
                    player_count += len(snapshot['teamInfo'][team]['players'])

            # ToDo: get map from keeper...
            async with session.get(url_map, headers=headers) as r:
                data = await r.json()
                # map
                map_name = self.get_readable_map_name(
                    data['message']['SERVER_INFO']['map'])

        except (TypeError, aiohttp.ClientError, aiohttp.ContentTypeError):
            logging.warning(f'Server with guid {server_guid} is offline.')
            async with self.lock:
                self._cur_activity_players = self._cur_activity_map = \
                    discord.Game(name='offline')
                self._cur_activity_map = self._cur_activity_players
                self._cur_status = discord.Status.dnd
                return None

        # process the received data

        # do not show values > max_players
        player_count = numpy.clip(player_count, 0, max_slots)

        # online
        if player_count / max_slots >= 0.6:
            status = discord.Status.online
        # afk
        elif player_count / max_slots >= 0.35:
            status = discord.Status.idle
        # dnd
        else:
            status = discord.Status.dnd

        # text for player count
        player_str = f'{player_count}/{max_slots} '
        if queue > 0:
            player_str += f'[{queue}] '
        player_str += 'online players'

        # create new activities
        activity_players = discord.Activity(name=player_str,
                                            type=discord.ActivityType.watching)
        activity_map = discord.Game(name=map_name)

        last_player_count = self._last_player_count
        self._last_player_count = player_count
        if (last_player_count
                and player_count == 0
                and last_player_count > 0):
            await asyncio.sleep(30)
            return last_player_count

        async with self.lock:
            self._cur_activity_players = activity_players
            self._cur_activity_map = activity_map
            self._cur_status = status
        return player_count

    async def set_presence(self, activity: discord.Activity,
                           status: discord.Status):
        """
        Changes the discord presence
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
            logging.critical(
                'Called discord.Client.change_presence with an '
                'invalid argument.')
        except ConnectionResetError as e:
            logging.exception(e)

    async def monitor(self, server_guid: str, check_map: bool = True,
                      interval_presence_change: int = 20,
                      interval_battlelog_fetch: int = 20):
        """
        Monitor the given server and display the status in the bot's presence.
        :param server_guid: guid of the BF4 server to monitor
        :param check_map: should the bot also show the map?
            default: True
        :param interval_presence_change: delay between presence changes in s
            default: 20 seconds
        :param interval_battlelog_fetch: delay between Battlelog requests
            default: 20 seconds
        """

        async def monitor_server():
            """asyncio task for fetching new data from Battlelog"""
            async with aiohttp.ClientSession(trust_env=True) as session:
                while True:
                    # data is cached in members by self.get_server_status
                    try:
                        await self.get_server_status(session, server_guid)
                    except aiohttp.ClientError as e:  # ...
                        logging.error(
                            'Error while fetching data from Battlelog!')
                        logging.exception(e)
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
