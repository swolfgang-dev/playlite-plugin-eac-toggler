# EasyAntiCheat Toggler for Playlite

An independent native Linux plugin for **Elden Ring**. In a game's plugin actions, choose **Disable EasyAntiCheat (offline)** or **Enable EasyAntiCheat**. Supports the installation root or its `Game` subfolder.

Disabling backs up `start_protected_game.exe`, replaces it with the game's executable, and creates `steam_appid.txt` only if needed. Enabling restores the original launcher and removes only the unchanged app-ID file created by this plugin. Existing matching app-ID files are preserved. Close the game before toggling. Disabled EAC means offline play.

Game updates or external launcher changes are detected before launching through Playlite. If files change, verify them through Steam before proceeding. Removing this plugin does not restore modified game files: enable EAC before removing it.

Inspired by [techiew/EldenRingEacToggler](https://github.com/techiew/EldenRingEacToggler), whose scope is also Elden Ring. This is an independent implementation, without upstream code or binaries. It does not include the upstream Windows wrapper, winhttp proxy guard, or mod toggling. The update check applies to launches through Playlite.

Run tests with `python3 -m unittest discover -s tests -v`. Build a release with `python3 tools/build_release.py`.
