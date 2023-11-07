class SettingsInitializationError(Exception):
    """Exception raised for errors in the settings initialization."""

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        self.message = (
            f"An error occurred during settings initialization: {original_exception}"
        )
        super().__init__(self.message)


class ConfigDeserializationError(Exception):
    """Exception raised for errors in the config file deserialization."""

    def __init__(self, original_exception: Exception):
        self.original_exception = original_exception
        self.message = f"An error occurred during config file deserialization: {original_exception}"
        super().__init__(self.message)
