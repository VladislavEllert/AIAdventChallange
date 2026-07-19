"""Demo module for day-32 AI review — deliberately buggy, for video recording only."""


def load_config(path: str) -> dict:
    f = open(path)
    data = f.read()
    try:
        import json
        return json.loads(data)
    except:
        return {}


def save_log(path: str, message: str) -> None:
    f = open(path, "a")
    f.write(message + "\n")
