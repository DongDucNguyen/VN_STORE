import re,json
from pathlib import Path
from html.parser import HTMLParser
P=Path(__file__).resolve().parent/'raw'
class Tags(HTMLParser):
    def __init__(self,s):
        super().__init__(); self.tags=[]; self.feed(s)
    def handle_starttag(self,tag,attrs): self.tags.append((tag,dict(attrs)))
def links(key):
    return list(dict.fromkeys(a['href'] for t,a in Tags((P/f'{key}.raw').read_text(encoding='utf-8')).tags if t=='a' and 'href' in a))
if __name__=='__main__':
    print('ML', [x for x in links('minhlong-list') if '/products/' in x or 'page=' in x])
    print('HN',links('hanoia-home')[:110])
    print((P/'hanoia-robots.raw').read_text())
    j=json.loads((P/'minhlong-example.raw').read_text(encoding='utf-8'))
    print('MLJSON',json.dumps(j,ensure_ascii=False)[:3500])
