from agents import function_tool


@function_tool
def get_weather(city: str) -> str:
    """Return the weather for a given city."""
    return f"The weather in {city} is sunny."
