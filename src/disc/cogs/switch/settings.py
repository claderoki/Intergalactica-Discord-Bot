from .base_settings import SwitchCode


class FriendCodeSetting(SwitchCode):
    """Your Nintendo switch friend code"""
    switch_code_prefix = "SW"
    code = "friend_code"
    symbol = "🎮"


class CreatorCodeSetting(SwitchCode):
    """Your creator code"""
    switch_code_prefix = "MA"
    code = "creator_code"
    symbol = "🎮"


class DreamAddressSetting(SwitchCode):
    """Your dream address code"""
    switch_code_prefix = "DA"
    code = "dream_address"
    symbol = "🎮"
