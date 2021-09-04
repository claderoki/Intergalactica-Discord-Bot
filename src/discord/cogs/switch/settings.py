from src.discord.helpers.settings.base import UserSettingModel, ValidationResult

class FriendCodeSetting(UserSettingModel):
    code    = "friend_code"
    type    = UserSettingModel.BaseType.string
    example = "SW-XXXX-XXXX-XXXX"
    symbol  = "🎮"

    def validate(self) -> ValidationResult:
        result = self.base_validation()

        if len(self.value) != 17:
            result.add_error(f"{self.value} is not a valid friendcode")

        return result

    def sanitize(self):
        numbers = [x for x in self.value if x.isdigit()]
        length = len(numbers)
        new_chars = ["S", "W"]
        for i in range(12):
            if i in (0, 4, 8):
                new_chars.append("-")
            if i < length:
                new_chars.append(str(numbers[i]))
        self.value = "".join(new_chars)