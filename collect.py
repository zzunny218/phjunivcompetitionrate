"""Fetch each source once, match an unambiguous admission/department, retain stale data."""
import concurrent.futures
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
def norm(s):
    return re.sub(r'[^a-z0-9가-힣]', '', unicodedata.normalize('NFKC', s).lower())

def fetch(url):
    # Only follow frames belonging to the two supplied competition providers.
    for _ in range(4):
        r = requests.get(url, timeout=35)
        r.raise_for_status()
        raw = r.content
        charset = re.search(br'charset\s*=\s*["\x27]?([\w-]+)', raw[:8000], re.I)
        encoding = charset.group(1).decode() if charset else r.apparent_encoding
        soup = BeautifulSoup(raw.decode(encoding or 'utf-8', errors='replace'), 'html.parser')
        if soup.find('table'):
            return soup, url
        frame = soup.find(['frame', 'iframe'], src=True)
        if not frame:
            raise ValueError('경쟁률 표를 찾지 못했습니다')
        url = urljoin(url, frame['src'])
        if urlparse(url).hostname not in {'ratio.uwayapply.com', 'addon.jinhakapply.com'}:
            raise ValueError('지원하지 않는 원본 주소')
    raise ValueError('원본 표 연결 실패')

def extract(soup, target):
    candidates = []
    headings = []
    for table in soup.find_all('table'):
        heading = table.find_previous(['h2', 'h3', 'h4'])
        caption = table.find('caption')
        title = caption.get_text(' ', strip=True) if caption else ''
        if heading:
            title += ' ' + heading.get_text(' ', strip=True)
        headings.append(title.strip())
        if not all(norm(t) in norm(title) for t in target['terms']):
            continue
        # Rowspans are expanded so merged college names do not shift the counts.
        spans = {}
        for row in table.find_all('tr'):
            cells = {}
            for col, (value, left) in list(spans.items()):
                cells[col] = value
                if left <= 1: del spans[col]
                else: spans[col] = (value, left - 1)
            col = 0
            for cell in row.find_all(['th', 'td'], recursive=False):
                while col in cells: col += 1
                value = cell.get_text(' ', strip=True)
                width, height = int(cell.get('colspan', 1)), int(cell.get('rowspan', 1))
                for c in range(col, col + width):
                    cells[c] = value
                    if height > 1: spans[c] = (value, height - 1)
                col += width
            values = [cells[c] for c in sorted(cells)]
            if len(values) < 4: continue
            labels = values[:-3]
            if not any(norm(alias) == norm(label) for alias in target['departments'] for label in labels):
                continue
            quota, applicants, ratio = values[-3:]
            if not re.fullmatch(r'[\d,]+', quota) or not re.fullmatch(r'[\d,]+', applicants): continue
            if not re.fullmatch(r'\s*[\d,.]+\s*:\s*1\s*', ratio): continue
            candidates.append(dict(quota=int(quota.replace(',', '')), applicants=int(applicants.replace(',', '')), ratio=ratio, matched_admission=title.strip(), matched_department=' / '.join(labels)))
    if len(candidates) != 1:
        raise ValueError(f'전형·학과 일치 {len(candidates)}건: 원본 확인 필요')
    return candidates[0]

def main():
    targets = json.loads((ROOT / 'targets.json').read_text())
    path = ROOT / 'data.json'
    previous = {r['id']: r for r in json.loads(path.read_text()).get('rows', [])} if path.exists() else {}
    now = datetime.now(ZoneInfo('Asia/Seoul')).isoformat(timespec='seconds')
    pages = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        jobs = {pool.submit(fetch, url): url for url in dict.fromkeys(t['url'] for t in targets)}
        for job in concurrent.futures.as_completed(jobs):
            try: pages[jobs[job]] = job.result()
            except Exception as e: pages[jobs[job]] = e
    rows = []
    for t in targets:
        row = {**t, 'checked_at': now}
        try:
            page = pages[t['url']]
            if isinstance(page, Exception): raise page
            soup, source = page
            if any(s in soup.get_text() for s in ['서비스 오픈전입니다', '서비스 오픈 전입니다']):
                raise ValueError('공개 전')
            row.update(extract(soup, t))
            old = previous.get(t['id'], {})
            if 'ratio' in old:
                row['previous_ratio'] = old['ratio']
                row['previous_success'] = old.get('last_success')
            row.update(status='ok', last_success=now, source_url=source)
            stamp = soup.select_one('#ID_DateStr')
            if stamp:
                row['source_time'] = stamp.get_text(' ', strip=True)
            else:
                match = re.search(r'20\d\d-\d\d-\d\d\s+(?:오전|오후)\s*\d+:\d+\s*현황', soup.get_text(' ', strip=True))
                row['source_time'] = match.group(0) if match else '원본 기준 시각 확인 불가'
        except Exception as e:
            old = previous.get(t['id'], {})
            for key in ['quota', 'applicants', 'ratio', 'last_success', 'source_url', 'matched_admission', 'matched_department', 'previous_ratio', 'previous_success', 'source_time']:
                if key in old: row[key] = old[key]
            row.update(status='stale' if 'ratio' in row else 'pending', error=str(e)[:180])
        rows.append(row)
        print(t['id'], row['status'], row.get('ratio', row.get('error')))
    result = {'checked_at': now, 'rows': rows}
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)

if __name__ == '__main__': main()
