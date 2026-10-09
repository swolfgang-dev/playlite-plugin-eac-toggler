from pathlib import Path
from PyQt6.QtWidgets import QMessageBox
from playlite.providers import GenericPlugin,IntegrationPlugin
from .toggler import folder,status,disable,enable,STATE


class Plugin(GenericPlugin):
    def game_actions(self,window,game):
        directory=game.get('InstallDirectory')
        if not directory:return []
        try:root=folder(directory)
        except (ValueError,OSError):return []
        if (root/STATE).exists():return [('Enable EasyAntiCheat…',lambda:self.toggle(window,game,True))]
        return [('Disable EasyAntiCheat (offline)…',lambda:self.toggle(window,game,False))]

    def toggle(self,window,game,restore):
        try:
            if window.game_detection.status(game['Id']) in ('Launching','Running'):
                raise ValueError('Close the game before changing EasyAntiCheat.')
            for provider in window.game_providers:
                if isinstance(provider,IntegrationPlugin) and provider.owns(game) and game['Id'] in provider.detect_running([game]):
                    raise ValueError('Close the game before changing EasyAntiCheat.')
            title='Enable EasyAntiCheat' if restore else 'Disable EasyAntiCheat'
            message='Restore the original launcher?' if restore else 'Disable EasyAntiCheat for Elden Ring? This forces offline play. The original launcher will be backed up.'
            if QMessageBox.question(window,title,message)!=QMessageBox.StandardButton.Yes:return
            (enable if restore else disable)(game['InstallDirectory'])
            message='EasyAntiCheat enabled.' if restore else 'EasyAntiCheat disabled for offline play.'
            if hasattr(window,'statusBar'):window.statusBar().showMessage(message,8000)
            else:QMessageBox.information(window,title,message)
        except (ValueError,OSError,KeyError) as error:QMessageBox.warning(window,'EasyAntiCheat Toggler',str(error))

    def before_launch(self,window,game):
        directory=game.get('InstallDirectory')
        if not directory:return True
        base=Path(directory)
        if not any((root/STATE).exists() for root in (base,base/'Game')):return True
        try:
            if status(directory)!='Disabled':raise ValueError('Game files changed after disabling EAC. Verify game files in Steam before launching.')
        except (ValueError,OSError,KeyError) as error:
            QMessageBox.warning(window,'EasyAntiCheat Toggler',str(error));return False
        return True
