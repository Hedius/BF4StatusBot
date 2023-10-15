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

import logging

import nextcord
from nextcord import Intents

from .ServerMonitor.ServerMonitor import ServerMonitor


class BF4StatusBot(nextcord.Client):
    """
    Discord bot to display the true player count and the current map as a
    bot status.
    """

    def __init__(self, settings):
        intents = Intents().default()
        super().__init__(intents=intents)
        self.settings = settings

    async def on_ready(self):
        monitor = ServerMonitor(self)
        await monitor.monitor(self.settings.GAME,
                              (self.settings.SERVER_GUID
                               if 'SERVER_GUID' in self.settings
                               else self.settings.SERVER_NAME),
                              self.settings.as_bool('CHECK_MAP'),
                              self.settings.as_int('INTERVAL_PRESENCE_CHANGE'),
                              self.settings.as_int('INTERVAL_DATA_FETCH'))

    async def on_guild_join(self, guild):
        logging.info(
            'Joined Guild '
            f'{guild.name} / {guild.id} / In {len(self.guilds)} guilds'
        )

    async def on_guild_remove(self, guild):
        logging.info(
            'Left Guild '
            f'{guild.name} / {guild.id} / In {len(self.guilds)} guilds'
        )
