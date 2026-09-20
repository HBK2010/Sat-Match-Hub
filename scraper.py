import json
import re
import sys
from datetime import datetime
from bs4 import BeautifulSoup
import cloudscraper

TARGET_URL = "https://liveonsat.com/quickindex.html"


def get_real_matches():
  scraper = cloudscraper.create_scraper(
      browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
  )

  headers = {
      'Accept': (
          'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
      ),
      'Accept-Language': 'en-US,en;q=0.9',
      'Referer': 'https://liveonsat.com/',
  }

  matches = []
  try:
    print('Connecting to LiveOnSat via cloudscraper...')
    res = scraper.get(TARGET_URL, headers=headers, timeout=20)
    print(f'Status Code: {res.status_code}')

    if res.status_code == 200:
      soup = BeautifulSoup(res.text, 'html.parser')
      tables = soup.find_all('table')

      for table in tables:
        rows = table.find_all('tr')
        current_league = 'مباراة اليوم'

        for row in rows:
          header = row.find(
              ['th', 'td'], class_=re.compile(r'comp|league', re.I)
          )
          if header and len(row.find_all('td')) <= 2:
            t = header.get_text(strip=True)
            if t and len(t) > 3:
              current_league = t

          text = row.get_text(separator=' ').strip()
          if ' vs ' in text or ' v ' in text or ' - ' in text:
            cols = row.find_all('td')
            if len(cols) >= 2:
              teams = None
              m_time = ''
              for c in cols:
                c_txt = c.get_text(strip=True)
                if ' vs ' in c_txt or ' v ' in c_txt:
                  teams = c_txt
                elif re.search(r'\d{1,2}:\d{2}', c_txt):
                  m_time = re.search(r'\d{1,2}:\d{2}', c_txt).group(0)

              if not teams:
                continue

              channels = []
              for link in row.find_all('a'):
                ch_name = link.get_text(strip=True)
                if not ch_name or len(ch_name) < 2 or 'more' in ch_name.lower():
                  continue

                sat_info = link.get('title', '')
                sat_match = re.search(r'(\d+\.?\d*°?[EW])', sat_info)
                sat_orbit = (
                    sat_match.group(1).replace('°', '')
                    if sat_match
                    else 'SAT'
                )

                channels.append({'name': ch_name, 'orbit': sat_orbit})

              if channels and m_time:
                matches.append({
                    'match': teams,
                    'league': current_league,
                    'time': m_time,
                    'channels': channels,
                })
  except Exception as e:
    print(f'Scraper Error: {e}')

  return matches


def main():
  matches = get_real_matches()

  if matches:
    print(f'Successfully fetched {len(matches)} real live matches!')
    output = {
        'updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
        'total': len(matches),
        'matches': matches,
    }
  else:
    print(
        'Warning: Real fetch returned 0 matches, keeping previous or basic'
        ' data.'
    )
    try:
      with open('matches.json', 'r', encoding='utf-8') as f:
        output = json.load(f)
    except Exception:
      output = {
          'updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
          'total': 0,
          'matches': [],
      }

  with open('matches.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
  main()
