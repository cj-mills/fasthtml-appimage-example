#!/usr/bin/env python3
"""
Minimal FastHTML application demonstrating AppImage packaging.
"""

from fasthtml.common import *
import os
import sys
import subprocess
import platform
import socket
import webbrowser
from contextlib import closing
from datetime import datetime
import tempfile
from pathlib import Path

# Find an available port
def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

# Get port from environment or find a free one
PORT_ENV = os.environ.get('FASTHTML_PORT', '0')
PORT = int(PORT_ENV) if PORT_ENV != '0' else find_free_port()
HOST = os.environ.get('FASTHTML_HOST', '127.0.0.1')

# Setup writable directory for session keys and other files
# Use temp directory when running from AppImage
if os.environ.get('APPIMAGE'):
    # Running from AppImage - use temp directory
    WORK_DIR = Path(tempfile.mkdtemp(prefix='fasthtml-app-'))
    os.chdir(WORK_DIR)
else:
    # Running normally - use current directory
    WORK_DIR = Path.cwd()

# Create the FastHTML app
app, rt = fast_app(
    hdrs=(
        Link(rel='stylesheet', href='https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css'),
        Script(src='https://unpkg.com/htmx.org@1.9.10'),
    ),
    title="FastHTML AppImage Demo"
)

# State for demo
todos = []
counter = 0

@rt('/')
def get():
    return Container(
        H1("FastHTML AppImage Demo"),
        P(f"Running on {platform.system()} {platform.release()}"),
        P(f"Python {sys.version.split()[0]} | Server: {HOST}:{PORT}"),
        Hr(),

        # Counter demo
        Div(
            H2("Counter Demo"),
            Div(
                Button("Increment",
                       hx_post="/increment",
                       hx_target="#counter",
                       hx_swap="innerHTML"),
                Span(f"Count: {counter}", id="counter", style="margin-left: 1rem;"),
            ),
        ),
        Hr(),

        # Todo demo
        Div(
            H2("Todo List Demo"),
            Form(
                Input(type="text", name="task", placeholder="Enter a task...", required=True),
                Button("Add Task", type="submit"),
                hx_post="/add-todo",
                hx_target="#todo-list",
                hx_swap="innerHTML",
                hx_on="htmx:afterRequest: this.reset()"
            ),
            Ul(*[Li(todo) for todo in todos], id="todo-list"),
        ),
        Hr(),

        # System info
        Div(
            H2("System Information"),
            Ul(
                Li(f"Process ID: {os.getpid()}"),
                Li(f"Working Directory: {os.getcwd()}"),
                Li(f"Temp Directory: {WORK_DIR}" if os.environ.get('APPIMAGE') else None),
                Li(f"AppImage: {'Yes' if os.environ.get('APPIMAGE') else 'No'}"),
                Li(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            ) if not os.environ.get('APPIMAGE') else Ul(
                Li(f"Process ID: {os.getpid()}"),
                Li(f"Working Directory: {WORK_DIR}"),
                Li(f"AppImage: Yes"),
                Li(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            ),
            Button("Refresh",
                   hx_get="/system-info",
                   hx_target="#system-info",
                   hx_swap="outerHTML"),
            id="system-info"
        ),
        Hr(),

        # Launch options
        Div(
            H2("Launch Options"),
            P("You can configure how this app opens:"),
            Ul(
                Li("Set FASTHTML_BROWSER=app for standalone window mode"),
                Li("Set FASTHTML_BROWSER=none to not open browser automatically"),
                Li("Default: Opens in your default browser"),
            ),
        ),
    )

@rt('/increment', methods=['POST'])
def increment():
    global counter
    counter += 1
    return Span(f"Count: {counter}", id="counter")

@rt('/add-todo', methods=['POST'])
def add_todo(task: str):
    todos.append(task)
    return Ul(*[Li(todo) for todo in todos], id="todo-list")

@rt('/system-info')
def system_info():
    if os.environ.get('APPIMAGE'):
        info_list = Ul(
            Li(f"Process ID: {os.getpid()}"),
            Li(f"Working Directory: {WORK_DIR}"),
            Li(f"AppImage: Yes"),
            Li(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
        )
    else:
        info_list = Ul(
            Li(f"Process ID: {os.getpid()}"),
            Li(f"Working Directory: {os.getcwd()}"),
            Li(f"AppImage: No"),
            Li(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
        )

    return Div(
        H2("System Information"),
        info_list,
        Button("Refresh",
               hx_get="/system-info",
               hx_target="#system-info",
               hx_swap="outerHTML"),
        id="system-info"
    )

def open_browser(url):
    """Open browser based on environment settings."""
    browser_mode = os.environ.get('FASTHTML_BROWSER', 'default').lower()

    if browser_mode == 'none':
        print(f"Server running at {url}")
        print("Browser auto-open disabled. Please open manually.")
        return

    if browser_mode == 'app':
        # Try to open in app mode (standalone window)
        print(f"Opening in app mode at {url}")

        # Try different browsers in app mode
        if sys.platform == 'linux':
            browsers = [
                ['google-chrome', '--app=' + url],
                ['chromium', '--app=' + url],
                ['firefox', '--new-window', url],  # Firefox doesn't have true app mode
            ]

            for browser_cmd in browsers:
                try:
                    subprocess.Popen(browser_cmd,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    return
                except FileNotFoundError:
                    continue

    # Default: open in regular browser
    print(f"Opening in browser at {url}")
    webbrowser.open(url)

if __name__ == '__main__':
    import uvicorn
    import threading
    import time

    # The actual URL with the port we found
    url = f"http://{HOST}:{PORT}"

    # Open browser after a short delay
    timer = threading.Timer(1.5, lambda: open_browser(url))
    timer.daemon = True
    timer.start()

    print(f"Starting FastHTML server on {url}")

    # Run the server with the actual port
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")