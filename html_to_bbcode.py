import bs4
from bs4 import BeautifulSoup
import typing
#from dateutil.parser import parse as parseDate
import re
from urllib.parse import urlencode
def bbcode_escape(s:str):
    return s.replace("[","[­")

def bbcode_escape_url(u:str):
  return u.replace("]","%5D")

def html_to_bbcode(hstr:str):
  bbcode=[]
  soup = BeautifulSoup(hstr, 'html.parser', preserve_whitespace_tags=['span', 'div', 'p'])
  msgs = soup.select('div.chatlog__message-primary')
  for msg in msgs:
    author=msg.select_one(".chatlog__author-name")
    date=msg.select_one(".chatlog__timestamp")

    if author is not None and date is not None:
      author=author.get_text()
      date=date.get_text()
      date = date.split(" ") #16-04-2026 02:02 PM
      date = date[1]+" "+date[2]
      bbcode.append("[h2]"+bbcode_escape(author)+" "+date+"[/h2]\n")
    msgContents = msg.select_one(".chatlog__markdown-preserve") or []
    for ch in msgContents:
      bbcode.append(msg_elem_to_bbcode(ch))
    bbcode.append("\n\n")
  return "".join(bbcode)

def msg_elem_to_bbcode(el:bs4.Tag):
  if isinstance(el,str):
    return bbcode_escape(el)
  
  rs=""
  rf=""
  if el.name=='strong':
    rs="[b]"
    rf="[/b]"
  elif el.name=='em':
    rs="[i]"
    rf="[/i]"
  elif el.name=="span":
    if el.has_attr("style"):
      st=el.attrs["style"]
      if "text-decoration: line-through" in st:
        rs="[s]"
        rf="[/s]"
    if el.has_attr("class"):
      cl=el.attrs["class"]
      if "spoiler--hidden" in cl:
        rs="[spoiler]"
        rf="[/spoiler]"
      elif "pre pre-inline" in cl:
        rs="[code]"
        rf="[/code]"
  elif el.name=="div":
    if el.has_attr("class"):
      cl = el.attrs["class"]
      if "pre--multiline" in cl:
        rs="[codeblock]"
        rf="[/codeblock]"
      elif "quote" in cl:
        rs="[quote]"
        rf="[/quote]"
      elif "chatlog__embed" in cl:
        return ""
  elif el.name=="a":
    if el.has_attr("href"):
      rs="[url="+bbcode_escape_url(str(el.attrs["href"]))+"]"
      rf="[/url]"
  elif el.name == "img":
    if el.has_attr("alt") and el.has_attr("class") and "emoji" in el.attrs["class"]:
      return str(el.attrs["alt"])
  
  if rs=="" and rf=="":
    rm=el.get_text()
  else:
    r=[]
    for child in el.children:
      r.append(msg_elem_to_bbcode(child))
    rm="".join(r)
  
  return rs+rm+rf

if __name__ == "__main__":
  with open("transcript-general.html", encoding='utf-8') as f:
    html=f.read()
  log = html_to_bbcode(html)
  print(log)
  pass