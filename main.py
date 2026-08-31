# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import asyncio
from shared_client import start_client
import importlib
import os
import sys
import traceback
from flask import Flask
from threading import Thread

# ======================================================
# 🚀 Render Flask Web Server (To keep bot alive)
# ======================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

# ======================================================
# 🤖 Main Bot Logic
# ======================================================
async def load_and_run_plugins():
    try:
        await start_client()
    except Exception as e:
        print(f"❌ Error during start_client: {e}")
        traceback.print_exc()

    plugin_dir = "plugins"
    if os.path.exists(plugin_dir):
        plugins = [f[:-3] for f in os.listdir(plugin_dir) if f.endswith(".py") and f != "__init__.py"]
        for plugin in plugins:
            try:
                module = importlib.import_module(f"plugins.{plugin}")
                if hasattr(module, f"run_{plugin}_plugin"):
                    print(f"Running {plugin} plugin...")
                    await getattr(module, f"run_{plugin}_plugin")()  
            except Exception as e:
                print(f"❌ Error loading plugin {plugin}: {e}")
                traceback.print_exc()

async def main():
    await load_and_run_plugins()
    while True:
        await asyncio.sleep(1)  

if __name__ == "__main__":
    # Flask web server background me trigger
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("🌐 Web server successfully bound to port 5000...")

    loop = asyncio.get_event_loop()
    print("Starting clients ...")
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
    except Exception as e:
        print(f"⚠️ Caught critical main loop exception: {e}")
        traceback.print_exc()
        # PERMANENT FIX: sys.exit(1) ko block kiya taaki Render restart loop me na phase
        print("Keep-alive active. Main process continuing...")
        loop.run_until_complete(main())
