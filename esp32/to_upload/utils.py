# Standard library imports
import socket
import sys
import uio
import os

def resolve_mdns_hostname(hostname):
    """
    Resolves the provided hostname using the mDNS protocol.

    :param hostname: str - The hostname to be resolved
    :return: str - The resolved IP address
    """
    addr_info = socket.getaddrinfo(hostname, 1883)
    return addr_info[0][-1][0]
    

def debug_print(file_name, line_number, *args, **kwargs):
    """
    Prints a debug message with the filename and line number.

    :param file_name: str - The name of the file
    :param line_number: int - The line number
    :param args: tuple - Additional messages to be included in the debug print
    :param kwargs: dict - Additional keyword arguments to be included in the debug print, formatted as key=value
    """
    print(f"[DEBUG] {file_name}:{line_number}", *args, **kwargs)



def print_log(message, error=False, exc=None):
    """
    Prints a log message.

    :param message: str - The message to be included in the log print
    :param error: bool - If True, prints an error message
    :param exc: Exception - An exception object to include in the log print
    """
    log_type = "[ERROR]" if error else "[LOG]"
    log_message = f'{log_type} {message}'

    if error and exc:
        traceback_str = convert_traceback(exc)
        log_message += f"\n\tException traceback: {traceback_str}"

    print(log_message)


def convert_traceback(exc):
    """
    Converts an error message to a traceback string.

    :param exc: Exception - The exception object
    :return: str - The formatted traceback as a string
    """

    # Create a StringIO object to capture the traceback
    traceback_str = uio.StringIO()
    sys.print_exception(exc, traceback_str)

    return traceback_str.getvalue()


