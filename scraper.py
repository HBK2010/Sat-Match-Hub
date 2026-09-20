import datetime
import json
import re
import urllib.request
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

# رابط جدول مباريات اليوم المباشر الشامل لكل الدوريات
TARGET_URL = "https://www.livesoccertv.com/"


def clean_text(text):
  return re.sub(r"\s+", " ", text).strip() if text else ""


def parse_matches():
  matches = []
  try:
    print("Fetching today's schedule (European & Arab Leagues)...")
    req = urllib.request.Request(TARGET_URL, headers=HEADERS)
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8")
    soup = BeautifulSoup(html, "html.parser")

    # استخراج الجداول المنظمة للمباريات
    match_rows = soup.find_all(
        "tr", class_=re.compile(r"matchrow|live", re.I)
    ) or soup.find_all("tr")

    for row in match_rows:
      text = row.get_text()
      if " vs " in text or " - " in text or ":" in text:
        # 1. استخراج الدوري / البطولة
        league_elem = row.find_previous(
            ["th", "div", "span"],
            class_=re.compile(r"league|competition|comp", re.I),
        )
        league_name = (
            clean_text(league_elem.get_text()) if league_elem else "مباراة اليوم"
        )

        # 2. استخراج التوقيت
        time_m = re.search(r"\b(\d{1,2}:\d{2})\b", text)
        if not time_m:
          continue
        m_time = time_m.group(1)

        # 3. استخراج أسماء الفريقين
        teams_elem = row.find(
            ["td", "span", "a"],
            class_=re.compile(r"match|teams|fixture", re.I),
        )
        match_title = ""
        if teams_elem:
          match_title = clean_text(teams_elem.get_text())
        else:
          for td in row.find_all("td"):
            td_txt = clean_text(td.get_text())
            if " vs " in td_txt or " - " in td_txt:
              match_title = td_txt
              break

        if not match_title or len(match_title) < 5:
          continue

        # 4. استخراج القنوات الناقلة (عربية وأوروبية)
        channels = []
        ch_container = row.find(
            ["td", "div"], class_=re.compile(r"channel|tv|broadcast", re.I)
        )
        if ch_container:
          links = ch_container.find_all(["a", "span"])
          for l in links:
            ch_name = clean_text(l.get_text())
            if ch_name and len(ch_name) > 1 and "more" not in ch_name.lower():
              # تخمين المدار بناء على اسم القناة
              orbit = "SAT"
              lower_ch = ch_name.lower()
              if any(
                  x in lower_ch
                  for x in ["canal+", "polsat", "eleven", "nova", "sportklub"]
              ):
                orbit = "13.0E"
              elif any(
                  x in lower_ch
                  for x in ["dazn", "movistar", "sky sport", "la liga tv"]
              ):
                orbit = "19.2E"
              elif any(
                  x in lower_ch
                  for x in ["bein", "ssc", "ontime", "alkass", "ad sports"]
              ):
                orbit = "7.0W"

              channels.append({"name": ch_name, "orbit": orbit})

        if channels:
          matches.append({
              "match": match_title,
              "league": league_name,
              "time": m_time,
              "channels": channels,
          })

  except Exception as e:
    print(f"Fetch Error: {e}")

  return matches


def main():
  data = parse_matches()
  if data:
    print(f"Successfully scraped {len(data)} matches!")
    output = {
        "updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "total": len(data),
        "matches": data,
    }
    with open("matches.json", "w", encoding="utf-8") as f:
      json.dump(output, f, ensure_ascii=False, indent=2)
  else:
    print("No new data fetched.")


if __name__ == "__main__":
  main()
