# Refactoring Proposal: Split fingr.py into Modules

## Overview

This branch proposes splitting the monolithic `fingr.py` (748 lines) into a modular structure for improved maintainability and organization.

## New Structure

```
fingr/
├── __init__.py          # Package metadata (__version__, __url__, __license__)
├── config.py            # Configuration loading (user agent, motd, denylist)
├── location.py          # Location resolution and timezone handling
├── weather.py           # Weather data fetching and wind chill calculation
├── formatting.py        # Meteogram and output formatting
├── server.py            # Server and request handling
└── utils.py             # Utility functions (wind direction, input cleaning)
```

## Module Responsibilities

### `fingr/__init__.py` (4 lines)
- Package version and metadata

### `fingr/config.py` (~80 lines)
- `load_user_agent()` - Load user agent from file
- `load_motd_list()` - Load message of the day list
- `random_message()` - Pick random MOTD
- `load_deny_list()` - Load IP denylist

### `fingr/utils.py` (~40 lines)
- `wind_direction()` - Convert degrees to compass direction
- `clean_input()` - Sanitize user input

### `fingr/location.py` (~80 lines)
- `get_timezone()` - Get timezone for coordinates
- `resolve_location()` - Geocode location names, handle caching
- Type aliases: `RedisClient`, `Timezone`
- Global: `timezone_finder`

### `fingr/weather.py` (~30 lines)
- `fetch_weather()` - Get forecast from met.no API
- `calculate_wind_chill()` - Wind chill calculation

### `fingr/formatting.py` (~320 lines)
- `sun_up()` - Check if sun is up at location/time
- `format_meteogram()` - Main meteogram formatting logic
- `print_units()` - Add unit labels to meteogram
- `print_meteogram_header()` - Generate meteogram header
- `format_oneliner()` - One-line forecast format
- Constants: `weather_legend`

### `fingr/server.py` (~200 lines)
- `handle_request()` - Handle incoming finger requests
- `start_server()` - Initialize server and dependencies
- `service_usage()` - Usage/help text
- Global runtime objects: `r`, `geolocator`, `denylist`, `motdlist`, `user_agent`

### `fingr_refactored.py` (~40 lines)
- Main entry point
- Argument parsing
- Logging setup

## Benefits

1. **Separation of Concerns**: Each module has a clear, focused responsibility
2. **Easier Testing**: Modules can be tested in isolation
3. **Better Navigation**: Developers can quickly find relevant code
4. **Reduced Complexity**: Smaller files are easier to understand
5. **Improved Maintainability**: Changes to one area don't affect others
6. **Type Safety**: Clearer module boundaries help with type checking

## Running the Refactored Version

```bash
# Same as before, just use the new entry point
python3 fingr_refactored.py --host 127.0.0.1 --port 7979
```

## Compatibility

The refactored version maintains 100% functional compatibility with the original. All features, command-line arguments, and behaviors are preserved.

## Migration Path

1. Review this branch
2. Test thoroughly with existing test suite
3. If approved, replace `fingr.py` with the modular structure
4. Update `pyproject.toml` if needed for package structure

## Testing

Run the existing test suite to verify compatibility:

```bash
python3 -m unittest fingr_test.py
```

## Files Changed

- **New**: `fingr/` package directory with 7 module files
- **New**: `fingr_refactored.py` - New entry point
- **Unchanged**: `fingr.py` - Original file kept for comparison
- **Added**: `REFACTORING.md` - This document
