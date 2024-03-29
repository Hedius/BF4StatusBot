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
import asyncio
import json
import logging
import re
from enum import Enum
from typing import Optional

import aiohttp
import nextcord
import numpy
import pkg_resources


class ServerMonitor:
    """
    Shows the current map and player count of the given BF4 server
    in the bot's Discord presence
    """
    class Games(Enum):
        BF4 = 'BF4'
        BBR = 'BBR'

    def __init__(self, bot: nextcord.Client):
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
            maps = json.load(file)
            self.maps = {}
            for cur_map in maps:
                self.maps[cur_map.upper()] = maps[cur_map]

    def get_readable_map_name(self, engine_name: str) -> str:
        """
        Convert the engine name of the given map to the
        its human-readable name
        :param engine_name: string: e.g. MP_Damage
        :return: human-readable name
        """
        if engine_name.upper() in self.maps:
            return self.maps[engine_name.upper()]
        return f'unknown map: {engine_name}'

    async def get_bbr_server_status(self, session: aiohttp.ClientSession,
                                    server_id: str) -> Optional[int]:
        """
        Get the player count and current map of the given server
        Also saves the result in class members
        :param session: aiohttp session
        :param server_id: name of the server. matchin here by name.
        :returns: the current player count. (None if the server is offline)
        """
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip,deflate'
        }
        url = 'https://publicapi.battlebit.cloud/Servers/GetServerList'
        try:
            async with session.get(url, headers=headers) as r:
                # Dirty... :)
                data = (await r.text()).encode().decode('utf-8-sig')
                data = json.loads(data)
                rule = re.compile(rf'.*({server_id}).*', flags=re.IGNORECASE)
                matched = False
                for server in data:
                    if re.match(rule, server['Name']) is None:
                        continue
                    logging.info(f'Matched with BBR server {server["Name"]}')
                    max_slots = server['MaxPlayers']
                    queue = server['QueuePlayers']
                    # Map is in camel case. so split it.
                    map_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', server['Map'])
                    player_count = server['Players']
                    matched = True
                    break
                if not matched:
                    raise TypeError('Offline')

                await self.update_status(player_count, max_slots, queue,
                                         map_name)

        except (TypeError, aiohttp.ClientError, aiohttp.ContentTypeError, json.JSONDecodeError) as e:
            logging.error(f'Error while fetching status: {e}')
            async with self.lock:
                self._cur_activity_players = self._cur_activity_map = \
                    nextcord.Game(name='offline')
                self._cur_activity_map = self._cur_activity_players
                self._cur_status = nextcord.Status.dnd
                return None

    async def get_bf4_server_status(self, session: aiohttp.ClientSession,
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
        try:
            async with session.get(url_keeper, headers=headers) as r:
                data = await r.json()
                snapshot = data['snapshot']
                # players
                max_slots = snapshot['maxPlayers']
                queue = snapshot['waitingPlayers']
                current_map = snapshot['currentMap'].rsplit('/', 1)[1]
                map_name = self.get_readable_map_name(current_map)

                player_count = 0
                for team in snapshot['teamInfo']:
                    player_count += len(snapshot['teamInfo'][team]['players'])

        except (TypeError, aiohttp.ClientError, aiohttp.ContentTypeError):
            logging.warning(f'Server with guid {server_guid} is offline.')
            async with self.lock:
                self._cur_activity_players = self._cur_activity_map = \
                    nextcord.Game(name='offline')
                self._cur_activity_map = self._cur_activity_players
                self._cur_status = nextcord.Status.dnd
                return None

        # process the received data
        await self.update_status(player_count, max_slots, queue, map_name)

        # do not show values > max_players
        return int(player_count)

    async def update_status(self, player_count, max_slots,
                            queue, map_name):
        player_count = numpy.clip(player_count, 0, max_slots)

        # online
        if player_count / max_slots >= 0.6:
            status = nextcord.Status.online
        # afk
        elif player_count / max_slots >= 0.35:
            status = nextcord.Status.idle
        # dnd
        else:
            status = nextcord.Status.dnd

        # text for player count
        player_str = f'{player_count}/{max_slots} '
        if queue > 0:
            player_str += f'[{queue}]'
        player_str += f' on {map_name}'

        # create new activities
        activity_players = nextcord.Activity(
            name=player_str,
            type=nextcord.ActivityType.watching
        )
        activity_map = nextcord.Game(name=map_name)

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

    async def set_presence(self, activity: nextcord.Activity,
                           status: nextcord.Status):
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
        except nextcord.InvalidArgument:
            logging.critical(
                'Called discord.Client.change_presence with an '
                'invalid argument.')
        except ConnectionResetError as e:
            logging.exception(e)

    async def monitor(self, game: str, server_guid: str, check_map: bool = True,
                      interval_presence_change: int = 20,
                      interval_battlelog_fetch: int = 60):
        """
        Monitor the given server and display the status in the bot's presence.
        :param game: game string for server status.
        :param server_guid: guid of the BF4 server to monitor
        :param check_map: should the bot also show the map?
            default: True
        :param interval_presence_change: delay between presence changes in s
            default: 20 seconds
        :param interval_battlelog_fetch: delay between Battlelog requests
            default: 60 seconds
        """

        async def monitor_server():
            """asyncio task for fetching new data from Battlelog"""
            async with aiohttp.ClientSession(trust_env=True) as session:
                while True:
                    # data is cached in members by self.get_server_status
                    try:
                        if game.upper() == 'BBR':
                            await self.get_bbr_server_status(session, server_guid)
                        else:
                            await self.get_bf4_server_status(session, server_guid)
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
                await asyncio.sleep(interval_presence_change if check_map else interval_battlelog_fetch)

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
