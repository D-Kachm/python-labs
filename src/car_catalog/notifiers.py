class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"[CONSOLE NOTIFICATION] -> {recipient}: {message}")

class RecordingNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))

    def clear(self) -> None:
        self.messages.clear()

class EmailNotifier:
    def __init__(self, sender: str = "noreply@car-catalog.ua") -> None:
        self.sender = sender

    def send(self, recipient: str, message: str) -> None:
        print(f"[EMAIL FROM {self.sender}] -> {recipient}: {message}")
