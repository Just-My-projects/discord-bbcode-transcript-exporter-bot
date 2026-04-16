from threading import Thread
import asyncio
from aiohttp import web

async def handle(request:web.Request):
    id=request.match_info['id']
    if id in quick_copy_cache_dict:
       html=quick_copy_cache_dict[id]
       return web.Response(text=html,
                           content_type='text/html')
    else:
        return web.Response(text='404: no transcript with this id', status=404)

onbotwakeup=None
async def botwakeup(request:web.Request):
  if onbotwakeup is None:
    return web.Response(text="500: bot wakeup callback hasn't been assigned", status=500)
  onbotwakeup()
  return web.Response(text="Bot woken up successfully")

app = web.Application()
app.add_routes([web.get('/copy/{id}', handle)])
app.add_routes([web.get('/botwakeup', botwakeup)])

def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    web.run_app(app, port=10000)

def start_web_server_thread(onbotwakeup=None):
    loop = asyncio.new_event_loop()
    onbotwakeup=onbotwakeup
    t = Thread(target=start_background_loop, args=(loop,), daemon=True)
    t.start()


from collections import deque
from html import escape as htmlescape

quick_copy_cache = deque()
quick_copy_cache_dict = {}

def add_to_quick_copy(id,bbcode):
  html=make_quick_copy_html(bbcode)
  quick_copy_cache.append(id)
  quick_copy_cache_dict[id]=html
  if len(quick_copy_cache) > 6:
    del quick_copy_cache_dict[quick_copy_cache.popleft()]


with open("thirdparty_clipboard_copy.js","r",encoding="utf-8") as f:
  clipboard_copyjs= f.read()

def make_quick_copy_html(bbcode):
  return """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Transcript - copy to clipboard</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
</head>
<body>
<button onclick="copy()">Copy Transcript</button> <br><br><br>
<div id="log" style="white-space: pre;">""" + htmlescape(bbcode) + \
"""</div>
<script>""" +\
clipboard_copyjs +\
"""
log = document.querySelector('#log')
txt = log.textContent
function copy(){
  console.log("Trying to copy")
  s=copyTextToClipboard(txt)
  
}
</script>

</body>
</html>"""

import time
if __name__ == "__main__":
    start_web_server_thread()
    time.sleep(235235385)