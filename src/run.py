#!/usr/bin/env python3

__author__ = "Hedius"
__version__ = "1.1.0"
__license__ = "GPLv3"
__copyright__ = 'Copyright 2020 Hedius'

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
from dynaconf import LazySettings, Validator

from BF4StatusBot import BF4StatusBot

settings = LazySettings(
    SETTINGS_FILE_FOR_DYNACONF="settings.toml,default.toml,user.toml",
    ENVVAR_PREFIX_FOR_DYNACONF="BF4STATUSBOT",
    ENV_FOR_DYNACONF="BF4StatusBot"
)

settings.validators.register(Validator("BOT_TOKEN", must_exist=True))
settings.validators.register(Validator("INTERVAL_PRESENCE_CHANGE", must_exist=True, lte=120, gte=4))
settings.validators.register(Validator("INTERVAL_DATA_FETCH", must_exist=True, gte=15))
settings.validators.register(Validator("CHECK_MAP", must_exist=True))
settings.validators.register(Validator("SERVER_GUID", must_exist=True))
settings.validators.validate()


def main():
    logging.basicConfig(level=logging.INFO)

    BF4StatusBot(settings).run(settings.BOT_TOKEN)


if __name__ == "__main__":
    main()
