# src/modules/utils.py
import time
import json

LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

def log_message(level, message):
    """
    Logs a message with a specified level.

    Args:
        level: The log level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
        message: The message to log.
    """
    timestamp = time.time()
    
    if level == "DEBUG" and LOG_LEVEL == "DEBUG":
        print(f"[{timestamp}] DEBUG: {message}")
    elif level == "INFO" and (LOG_LEVEL == "DEBUG" or LOG_LEVEL == "INFO"):
        print(f"[{timestamp}] INFO: {message}")
    elif level == "WARNING" and (LOG_LEVEL == "DEBUG" or LOG_LEVEL == "INFO" or LOG_LEVEL == "WARNING"):
        print(f"[{timestamp}] WARNING: {message}")
    elif level == "ERROR" and (LOG_LEVEL == "DEBUG" or LOG_LEVEL == "INFO" or LOG_LEVEL == "WARNING" or LOG_LEVEL == "ERROR"):
        print(f"[{timestamp}] ERROR: {message}")
    elif level == "CRITICAL":
        print(f"[{timestamp}] CRITICAL: {message}")
    

def log_error(message):
    """
    Logs an error message.

    Args:
        message: The error message to log.
    """
    log_message("ERROR", message)

def log_info(message):
    """
    Logs an info message.

    Args:
        message: The info message to log.
    """
    log_message("INFO", message)

def log_debug(message):
    """
    Logs a debug message.

    Args:
        message: The debug message to log.
    """
    log_message("DEBUG", message)
    
def log_warning(message):
    """
    Logs a warning message.

    Args:
        message: The warning message to log.
    """
    log_message("WARNING", message)

def get_datetime_string():
    """
    Returns the current date and time as a formatted string.

    Returns:
        A string representing the current date and time.
    """
    current_time = time.localtime()
    year, month, day, hour, minute, second = current_time[:6]
    return f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

def save_data_to_file(filepath, data):
    """
    Saves data to a file.

    Args:
        filepath: The path to the file.
        data: The data to save (must be json compatible).
    """
    try:
        with open(filepath, "a") as f:
            f.write(json.dumps(data) + "\n") # Write each set of data on a new line
        log_info(f"Data saved to {filepath}")
    except Exception as e:
        log_error(f"Error saving data to file: {e}")