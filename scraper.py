import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def clean_text(text):
    if not text:
        return ""
    text = text.replace('\xa0', ' ').replace('\n', ' ').replace('\r', ' ')
    return ' '.join(text.split())

def parse_table_to_grid(table_html):
    rows = table_html.find_all('tr')
    grid = []
    for _ in rows:
        grid.append([])

    for r_idx, row in enumerate(rows):
        tds = row.find_all(['td', 'th'])
        col_idx = 0
        for td in tds:
            while col_idx < len(grid[r_idx]) and grid[r_idx][col_idx] is not None:
                col_idx += 1
            
            rs = int(td.get('rowspan', 1))
            cs = int(td.get('colspan', 1))
            
            raw_text = td.get_text(separator=" ", strip=True)
            val = clean_text(raw_text)
            
            for i in range(rs):
                for j in range(cs):
                    while len(grid[r_idx + i]) <= col_idx + j:
                        grid[r_idx + i].append(None)
                    grid[r_idx + i][col_idx + j] = val
                    
            col_idx += cs
    return grid

def scrape_bac_results(base_url,start_page=1, end_page=5):
    all_candidates = []

    for page_num in range(start_page, end_page + 1):
        url = base_url.format(page_num)
        print(f"Scraping data from: {url}...")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error at page {page_num}: {e}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')
        
        table = soup.find('table', id='mainTable')
        if not table:
            print(f"Table not found on page {page_num}.")
            continue

        candidate_rows = table.find_all('tr')[2:]
        js_data_list = []
        
        # remove js obfuscation and parse table
        for i in range(0, len(candidate_rows), 2):
            tr_str = str(candidate_rows[i])
            
            cod_match = re.search(r'LuatDePeBacalaureatEduRo\[.*?\]\s*=\s*"(.*?)"', tr_str)
            media_match = re.search(r'LuatDePe_BacalaureatEduRo\[.*?\]\s*=\s*"(.*?)"', tr_str)
            rez_match = re.search(r'Luat_DePe_BacalaureatEduRo\[.*?\]\s*=\s*"(.*?)"', tr_str)
            
            cod = cod_match.group(1).replace('<br>', '').strip() if cod_match else ""
            media = media_match.group(1).replace('<br>', '').strip() if media_match else ""
            rezultat = rez_match.group(1).replace('<br>', '').strip() if rez_match else ""
            
            js_data_list.append({
                'cod': cod,
                'media': media,
                'rezultat': rezultat
            })

        for script in soup(["script", "style"]):
            script.decompose()

        grid = parse_table_to_grid(table)
        
        candidate_idx = 0
        for i in range(2, len(grid), 2):
            if i + 1 >= len(grid):
                break
                
            row1 = grid[i]
            row2 = grid[i+1]
            
            def get_val(r, idx):
                if idx < len(r) and r[idx] is not None:
                    return r[idx]
                return ""

            js_data = js_data_list[candidate_idx] if candidate_idx < len(js_data_list) else {'cod': '', 'media': '', 'rezultat': ''}
            
            candidate_data = {
                "num": get_val(row1, 0),
                "id": js_data['cod'],
                "school": get_val(row1, 2),
                "county": get_val(row1, 3),
                "previous_class": get_val(row1, 4),
                "education_type": get_val(row1, 5),
                "specialization": get_val(row1, 6),
                
                "ro_oral": get_val(row1, 7),
                "ro_written": get_val(row1, 8),
                "ro_remark": get_val(row1, 9),
                "ro_final": get_val(row1, 10),
                
                "native_oral": get_val(row2, 11),
                "native_written": get_val(row2, 12),
                "native_remark": get_val(row2, 13),
                "native_final": get_val(row2, 14),
                
                "foreign": get_val(row1, 15),
                "foreign_final": get_val(row1, 16),
                
                "mandatory": get_val(row1, 17),
                "mandatory_written": get_val(row2, 17), 
                "mandatory_remark": get_val(row2, 18), 
                "mandatory_final": get_val(row2, 19), 
                
                "choice": get_val(row1, 20),
                "choice_written": get_val(row2, 20),
                "choice_remark": get_val(row2, 21),
                "choice_final": get_val(row2, 22),
                
                "digital_final": get_val(row1, 23),

                "average": js_data['media'],
                "passed": js_data['rezultat'] 
            }
            
            columns_to_keep = [
                # "num",
                "id",
                "ro_written",
                "ro_remark",
                "ro_final",
                # "average"
            ]

            candidate_idx += 1
            
            if candidate_data["id"]:
                filtered_candidate = {key: candidate_data[key] for key in columns_to_keep if key in candidate_data}            
                all_candidates.append(filtered_candidate)
                
        time.sleep(0.05)

    return pd.DataFrame(all_candidates)

if __name__ == "__main__":
    url1 = "https://static.bacalaureat.edu.ro/2025/rapoarte/rezultate/dupa_medie/page_{}.html"
    url2 = "https://static.bacalaureat.edu.ro/2024/rapoarte/rezultate/dupa_medie/page_{}.html"
    
    for url in [url1, url2]:
        df_results = scrape_bac_results(base_url=url, start_page=1, end_page=500)
        csv_filename = "results.csv"
        df_results.to_csv(csv_filename, index=False, encoding='utf-8-sig', mode='a')
        print(f"\nScrape for {url} finished! Data outputted to {csv_filename}")