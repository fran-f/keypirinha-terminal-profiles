#
# Windows Terminal Profiles plugin
# More info at https://github.com/fran-f/keypirinha-terminal-profiles
#

import keypirinha as kp

from .lib.WindowsTerminalWrapper import WindowsTerminalWrapper

class TerminalProfiles(kp.Plugin):
    """
    Add catalog items for all the profiles configured in Windows Terminal.
    """

    ICON_POSTFIX = ".scale-200.png"

    terminal = None
    default_icon = None
    profile_prefix = None
    use_profile_icons = False

    def on_start(self):
        self._load_settings()
        self._set_up()

    def on_events(self, flags):
        if flags & kp.Events.PACKCONFIG:
            self._clean_up()
            self._load_settings()
            self._set_up()

    def on_catalog(self):
        if not self.terminal:
            return

        self.set_catalog([
            self._item_for_profile(r) for r in self.terminal.profiles()
        ])

    def on_execute(self, item, action):
        self.terminal.openprofile(item.target())

    def on_suggest(self, user_input, items_chain):
        pass

    def _load_settings(self):
        """
        Load the configuration file and extract settings to local variables.
        """
        settings = PluginSettings(self.load_settings())
        self.terminal = WindowsTerminalWrapper(settings.settings_file(), \
                settings.executable())
        self.profile_prefix = settings.profile_prefix()
        self.use_profile_icons = settings.use_profile_icons()

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

    def _item_for_profile(self, profile):
        """
        Return a catalog item for a profile.
        """
        guid = profile.get("guid")
        icon = profile.get("icon", None)
        icon_handle = self._load_profile_icon(icon, guid) \
                if self.use_profile_icons else None

        return self.create_item(
                category = kp.ItemCategory.REFERENCE,
                label = self.profile_prefix + profile.get("name"),
                short_desc = "Open a new terminal",
                icon_handle = icon_handle,
                target = guid,
                args_hint = kp.ItemArgsHint.FORBIDDEN,
                hit_hint = kp.ItemHitHint.IGNORE
        )

    def _load_profile_icon(self, icon, guid):
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
            except:
                pass
        else:
            # could it be an external file?
            try:
                return self.load_icon(icon)
            except:
                pass

        return None

    def _resource(self, filename):
        return "res://Terminal-Profiles/resources/" + filename

class PluginSettings:

    def __init__(self, settings):
        self._settings = settings

    def settings_file(self):
        return self._settings.get(
                key = "settings_file",
                section = "terminal",
                fallback = WindowsTerminalWrapper.settings_file(),
                unquote = True
        );

    def executable(self):
        return self._settings.get(
                key = "executable",
                section = "terminal",
                fallback = WindowsTerminalWrapper.executable(),
                unquote = True
        );

    def profile_prefix(self):
        return self._settings.get(
                key = "profile_prefix",
                section = "items",
                fallback = "Windows Terminal: ",
                unquote = True
        )

    def use_profile_icons(self):
        return self._settings.get_bool(
                key = "use_profile_icons",
                section = "items",
                fallback = True
        )

