"""
Windows Terminal wrapper class
More info at https://github.com/fran-f/keypirinha-terminal-profiles
"""

# Disable warning for relative import statements
# pylint: disable=import-error, relative-beyond-top-level

import json
import os

import keypirinha_util as kpu
from .jsmin import jsmin

class WindowsTerminalWrapper:

    def __init__(self, settings, executable):
        if not os.path.exists(settings):
            raise ValueError("Could not find Windows Terminal settings at %s" % (settings))
        if not os.path.exists(executable) and not os.path.lexists(executable):
            raise ValueError("Could not find Windows Terminal at %s" % (executable))

        self._wt_settings = settings
        self._wt_executable = executable

    def profiles(self):
        with kpu.chardet_open(self._wt_settings, mode="rt") as terminal_settings:
            data = json.loads(jsmin(terminal_settings.read()))

        profiles = data.get("profiles")
        if not profiles:
            return []

        # the profile list can be 'profiles' itself, or nested under 'list'
        profiles_list = profiles.get("list", []) \
            if isinstance(profiles, dict) else profiles

        return [
            p for p in profiles_list if p.get('hidden', False) == False
        ]

    def openprofile(self, guid, elevate=False):
        if elevate:
            kpu.shell_execute(
                "cmd.exe",
                args=['/c', 'start', '', '/b', self._wt_executable, '--profile', guid],
                verb="runas"
            )
        else:
            kpu.shell_execute(self._wt_executable, args=['--profile', guid])
