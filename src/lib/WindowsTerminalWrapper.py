#
# Windows Terminal wrapper class
# More info at https://github.com/fran-f/keypirinha-terminal-profiles
#

import keypirinha_util as kpu

import json
import os
from .jsmin import jsmin

class WindowsTerminalWrapper:

    LOCALAPPDATA = kpu.shell_known_folder_path("{f1b32785-6fba-4fcf-9d55-7b8e7f157091}")

    def settings_file():
        terminal_package = "Microsoft.WindowsTerminal_8wekyb3d8bbwe"
        return WindowsTerminalWrapper.LOCALAPPDATA + \
            "\\Packages\\" + terminal_package + "\\LocalState\\settings.json"

    def executable():
        return WindowsTerminalWrapper.LOCALAPPDATA + "\\Microsoft\\WindowsApps\\wt.exe"

    def __init__(self, settings, executable):
        if not os.path.exists(settings):
            raise ValueError("Could not find Windows Terminal settings at %s" % (settings))
        if not os.path.exists(executable) and not os.path.lexists(executable):
            raise ValueError("Could not find Windows Terminal at %s" % (executable))

        self._wt_settings = settings
        self._wt_executable = executable

    def profiles(self):
        with kpu.chardet_open(self._wt_settings, mode="rt") as terminal_settings:
            data = json.loads(jsmin(terminal_settings.getvalue()))

        profiles = data.get("profiles")
        if not profiles:
            return []

        return [
            p for p in profiles.get("list", []) if p.get('hidden', False) == False
        ]

    def openprofile(self, guid):
        kpu.shell_execute(self._wt_executable, args=[ '--profile', guid ])
