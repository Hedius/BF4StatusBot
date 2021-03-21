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

import discord

from .ServerMonitor.ServerMonitor import ServerMonitor


class BF4StatusBot(discord.Client):
    """
    Discord bot to display the true player count and the current map as a
    bot status.
    """

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    async def on_ready(self):
        monitor = ServerMonitor(self)
        await monitor.monitor(self.settings.SERVER_GUID,
                              self.settings.as_bool('CHECK_MAP'),
                              self.settings.as_int('INTERVAL_PRESENCE_CHANGE'),
                              self.settings.as_int('INTERVAL_DATA_FETCH'))
