import sys
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.void_tags = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_tags:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.void_tags:
            return
        if not self.stack:
            print(f"Extra closing tag </{tag}> at line {self.getpos()}")
            return
        last, pos = self.stack[-1]
        if last == tag:
            self.stack.pop()
        else:
            print(f"Mismatched tag: expected </{last}> (opened at {pos}), got </{tag}> at {self.getpos()}")

parser = MyHTMLParser()
html = open('scratch/live_dash.html', encoding='utf-8').read()
parser.feed(html)
print(f"Done parsing. Unclosed tags: {len(parser.stack)}")
for t, pos in parser.stack[-10:]:
    print(f"  Unclosed <{t}> from {pos}")
