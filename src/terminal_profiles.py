"""
Windows Terminal Profiles plugin
More info at https://github.com/fran-f/keypirinha-terminal-profiles
"""

# Disable warning for relative import statements
# pylint: disable=import-error, relative-beyond-top-level

import os
import sys
import shutil

import keypirinha as kp
import keypirinha_util as kpu
from .lib.windows_terminal_wrapper import WindowsTerminalWrapper

class TerminalProfiles(kp.Plugin):
    """
    Add catalog items for all the profiles configured in Windows Terminal.
    """

    ACTION_OPEN = {
        'name' : "wt.open",
        'label' : "Open",
        'short_desc' : "Open this profile in a new window"
    }
    ACTION_OPEN_NEW_TAB = {
        'name' : "wt.open_new_tab",
        'label' : "Open new tab",
        'short_desc' : "Open this profile in a new tab of an existing window"
    }
    ACTION_ELEVATE = {
        'name' : "wt.elevate",
        'label' : "Run as Administrator",
        'short_desc' : "Open this profile in a new window with elevated privileges"
    }

    ICON_POSTFIX = ".scale-200.png"
    INSTANCE_SEPARATOR = "::"

    default_icon = None
    use_profile_icons = False

    terminal_instances = None

    def on_start(self):
        """Respond to on_start Keypirinha messages"""
        self._load_settings()
        self._set_up()

        actions = [
            self.ACTION_OPEN,
            self.ACTION_OPEN_NEW_TAB,
            self.ACTION_ELEVATE,
        ]
        self.set_actions(
            kp.ItemCategory.REFERENCE,
            [self.create_action(**a) for a in actions]
        )

    def on_events(self, flags):
        """Respond to on_events Keypirinha messages"""
        if flags & kp.Events.PACKCONFIG:
            self._clean_up()
            self._load_settings()
            self._set_up()

    def on_catalog(self):
        """Respond to on_catalog Keypirinha messages"""
        if not self.terminal_instances:
            return

        self.set_catalog([
            self._item_for_profile(instance, profile)
            for instance in self.terminal_instances.values()
            for profile in instance["wrapper"].profiles()
        ])

    def on_execute(self, item, action):
        """Respond to on_execute Keypirinha messages"""
        [instance, _, profile] = item.target().partition(self.INSTANCE_SEPARATOR)
        terminal = self.terminal_instances[instance]["wrapper"]

        if action is None:
            terminal.openprofile(profile)
            return

        if action.name() == self.ACTION_ELEVATE['name']:
            terminal.openprofile(profile, elevate=True)
        elif action.name() == self.ACTION_OPEN_NEW_TAB['name']:
            terminal.opennewtab(profile)
        else:
            terminal.openprofile(profile)

    def on_suggest(self, user_input, items_chain):
        """Respond to on_suggest Keypirinha messages"""
        # pass

    def _load_settings(self):
        """
        Load the configuration file and extract settings to local variables.
        """
        settings = PluginSettings(self)
        self.use_profile_icons = settings.use_profile_icons()

        self.terminal_instances = dict(settings.terminal_instances())

    def _set_up(self):
        """
        Initialise the plugin based on the extracted configuration.
        """
        self.default_icon = self.load_icon(self._resource("WindowsTerminal.png"))
        self.set_default_icon(self.default_icon)

    def _clean_up(self):
        """
        Clean up any resources, to start anew with fresh configuration.
        """
        if self.default_icon:
            self.default_icon.free()
            self.default_icon = None

    def _item_for_profile(self, instance, profile):
        """
        Return a catalog item for a profile.
        """
        guid = profile.get("guid")
        name = profile.get("name")
        if not guid or not name:
            self.warn("Skipping invalid profile with name:'%s' guid:'%s'" % (name, guid))
            return None

        icon = profile.get("icon", None)
        icon_handle = self._load_profile_icon(icon, guid) \
                if self.use_profile_icons else None

        return self.create_item(
            category=kp.ItemCategory.REFERENCE,
            label=instance["prefix"] + name,
            short_desc="Open a new terminal",
            icon_handle=icon_handle,
            target=instance["name"] + self.INSTANCE_SEPARATOR + guid,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.IGNORE
        )

    def _load_profile_icon(self, icon, guid):
        """
        Attempt to load an icon for the given profile.
        """
        iconfile = None
        if not icon:
            # check if this is a default profile
            if guid[0] == '{' and guid[-1] == '}':
                iconfile = self._resource(guid + self.ICON_POSTFIX)
        else:
            # internal icons ms-appx:///ProfileIcons/{...}.png
            if icon.startswith("ms-appx:///ProfileIcons/"):
                iconfile = self._resource(icon[24:-4] + self.ICON_POSTFIX)

        if iconfile:
            try:
                return self.load_icon(iconfile)
            except ValueError:
                pass
        else:
            # could it be an external file?
            try:
                # External files cannot be loaded as icon, so we try to copy it
                # to the plugin's cache directory, and load it from there.
                cache_dir = self.get_package_cache_path(True)
                icon_file = guid + ".ico"
                source = icon[8:] if icon[0:8] == "file:///" else os.path.expandvars(icon)
                shutil.copyfile(source, cache_dir + "\\" + icon_file)
                return self.load_icon("cache://Terminal-Profiles/" + icon_file)
            except (ValueError, FileNotFoundError, OSError):
                self.warn("Cannot load icon '%s' for profile %s" % (icon, guid))

        return None

    @staticmethod
    def _resource(filename):
        return "res://Terminal-Profiles/resources/" + filename


class PluginSettings:
    """Wrapper for the plugin configuration file."""

    INSTANCE_PREFIX = "terminal/"
    DEFAULT_ITEM_PREFIX = "Windows Terminal (%s): "

    LOCALAPPDATA = kpu.shell_known_folder_path("{f1b32785-6fba-4fcf-9d55-7b8e7f157091}")
    WINDOWSAPPS = LOCALAPPDATA + "\\Microsoft\\WindowsApps"

    PACKAGED_SETTINGS = LOCALAPPDATA + "\\Packages\\%s\\LocalState\\settings.json"
    PACKAGED_EXECUTABLE = WINDOWSAPPS + "\\%s\\wt.exe"

    MISSING_KEY_ERROR = """
        ⚠ Config section [%s] defines a custom installation, but the value for '%s' is missing.
    """

    def __init__(self, plugin):
        self._settings = plugin.load_settings()
        self._logger = plugin

    def use_profile_icons(self):
        """True if we should show try to load per-profile icons."""
        return self._settings.get_bool(
            key="use_profile_icons",
            section="items",
            fallback=True
        )

    def terminal_instances(self):
        """Return the list of terminal instances in the configuration file."""
        for section_name in self._instancesections():
            instance_name = section_name[len(self.INSTANCE_PREFIX):]

            # Skip an instance if it defines 'enabled = false'
            if not self._settings.get_bool(key="enabled", section=section_name, fallback=True):
                continue

            prefix = self._get(section_name, "prefix", "Windows Terminal (%s)" % (instance_name))
            app_package = self._get(section_name, "app_package")

            if app_package and not self._package_exists(app_package):
                self._logger.info(
                    "Skipping '%s', package %s does not exist" % (instance_name, app_package)
                )
                continue

            # For packaged instances, paths are derived from the package id...
            packaged_settings_file = self.PACKAGED_SETTINGS % (app_package) if app_package else None
            packaged_executable = self.PACKAGED_EXECUTABLE % (app_package) if app_package else None

            # ...but you can still override them
            settings_file = self._get(section_name, "settings_file", packaged_settings_file)
            executable = self._get(section_name, "executable", packaged_executable)

            # For custom instances, settings_file and executable are required
            if not app_package:
                if not settings_file:
                    self._logger.warn(self.MISSING_KEY_ERROR % (section_name, "settings_file"))
                    continue
                if not executable:
                    self._logger.warn(self.MISSING_KEY_ERROR % (section_name, "executable"))
                    continue

            self._logger.info(
                "Adding profiles for '%s' (%s)" % (instance_name, app_package or "custom")
            )
            try:
                wrapper = WindowsTerminalWrapper(settings_file, executable)
                yield (instance_name, {
                    "name": instance_name,
                    "prefix": prefix,
                    "wrapper": wrapper
                })
            except ValueError:
                message = sys.exc_info()[1]
                self._logger.warn(message)

    def _instancesections(self):
        return [
            s for s in self._settings.sections() \
                if s.lower().startswith(self.INSTANCE_PREFIX)
        ]

    def _get(self, section, key, fallback=None):
        return self._settings.get(key=key, section=section, fallback=fallback, unquote=True)

    def _package_exists(self, app_package):
        return os.path.exists(self.WINDOWSAPPS + "\\" + app_package)
