import re,json,sys
from pathlib import Path
from html.parser import HTMLParser
class Text(HTMLParser):
    def __init__(self,s): super().__init__(); self.parts=[]; self.skip=0; self.feed(s)
    def handle_starttag(self,t,a):
        if t in ('script','style'): self.skip+=1
    def handle_endtag(self,t):
        if t in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,d):
        if not self.skip and d.strip(): self.parts.append(d.strip())
def plain(s): return ' '.join(Text(s or '').parts)
if __name__=='__main__':
    for k in sys.argv[1:]:
        s=(Path(__file__).resolve().parent/'raw'/f'{k}.raw').read_text(encoding='utf-8')
        print(k,plain(s)[-15000:])
