from src.discord.helpers.settings.base import UserSettingModel, ValidationResult


class classproperty(property):
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()


class SwitchCode(UserSettingModel):
    type = UserSettingModel.BaseType.string

    def validate(self) -> ValidationResult:
        """This will validate the (sanitized) value for correctness."""
        result = self.base_validation()

        if len(self.value) != 17:
            result.add_error(f"{self.value} is not a valid code")

        return result

    def sanitize(self):
        numbers = [x for x in self.value if x.isdigit()]
        length = len(numbers)

        new_chars = [x for x in self.switch_code_prefix]
        for i in range(12):
            if i in (0, 4, 8):
                new_chars.append("-")
            if i < length:
                new_chars.append(str(numbers[i]))
        self.value = "".join(new_chars)

    @classproperty
    def example(self):
        return f"{self.switch_code_prefix}-XXXX-XXXX-XXXX"
