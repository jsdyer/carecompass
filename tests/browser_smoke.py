"""Exercise the real built app at its GitHub project subpath."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json, os, shutil, tempfile, threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def main():
 screenshots=ROOT/'browser-checks';screenshots.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as temp:
  shutil.copytree(ROOT/'dist',Path(temp)/ROOT.name)
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temp));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1280,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/assets/tool-metrics.js',lambda route:route.fulfill(status=200,body=''))
    page.route('https://tile.openstreetmap.org/**',lambda route:route.abort())
    page.goto(f'http://127.0.0.1:{server.server_port}/{ROOT.name}/');page.locator('.card').first.wait_for()
    page.locator('#query').fill('Halifax')
    page.locator('.card').first.get_by_role('button',name='Add to shortlist',exact=True).click()
    page.locator('.card').first.locator('textarea').fill('<img src=x onerror=alert(1)> Call Tuesday')
    page.locator('#query').click()
    page.reload();page.locator('.card').first.wait_for();page.locator('#saved-only').check()
    assert page.locator('.card').count()==1
    assert 'Call Tuesday' in page.locator('textarea').input_value()
    assert page.locator('#results img').count()==0
    with page.expect_download() as download:page.locator('#export').click()
    assert download.value.suggested_filename=='carecompass-shortlist.csv'
    page.locator('#reset').click();page.locator('#province').select_option('BC');page.locator('#query').fill('Surrey')
    assert page.locator('.card').count()>0
    page.locator('#show-map').click();assert page.locator('#map').is_visible()
    previous=json.loads((ROOT/'web/data/latest.json').read_text());previous['facilities']=previous['facilities'][:1];previous['checked_at']='2025-01-01T00:00:00Z'
    page.locator('#open-capture').set_input_files({'name':'earlier.json','mimeType':'application/json','buffer':json.dumps(previous).encode()})
    page.wait_for_function("document.querySelector('#storage-status').textContent.includes('2025-01-01')")
    page.locator('#reset').click()
    assert page.locator('.card').count()==1
    assert '2025-01-01' in page.locator('#sources').inner_text()
    page.locator('#show-map').click()
    page.route('**/data/latest.json*',lambda route:route.fulfill(status=503,body='temporarily unavailable'))
    page.reload();page.wait_for_function("document.querySelector('#status').textContent.includes('could not load')")
    page.unroute('**/data/latest.json*');page.reload();page.locator('.card').first.wait_for()
    page.screenshot(path=str(screenshots/'desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    page.screenshot(path=str(screenshots/'mobile.png'),full_page=True)
    assert not errors,errors;browser.close()
   print('Browser task, persistence, safe text, source failures and mobile layout passed')
  finally:server.shutdown()
if __name__=='__main__':main()
