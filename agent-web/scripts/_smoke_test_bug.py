"""Throwaway smoke-test file for AI-review Action (day 35.5, PR a: bug).

Not wired into the app. Deliberately contains a resource leak and a
silent bare except, to verify the review Action flags real bug patterns.
"""


def read_config_value(path, key):
    f = open(path)  # noqa: opened, never closed, no context manager
    lines = f.readlines()
    for line in lines:
        if line.startswith(key):
            try:
                return line.split("=", 1)[1].strip()
            except:  # noqa: bare except swallows any error silently
                pass
    return None
