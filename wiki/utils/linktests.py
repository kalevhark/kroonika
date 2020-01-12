#
# valgalinn.ee veebi testimiseks:
# küsib temaatilised lingid ja teeb sinna proovipäringud sõltuvalt nädalapäevast
#
from datetime import datetime
import os
import sys
import requests

def test_urls(path, server, url_list, urlvalik):
    filename = f'link_test_{datetime.now().strftime("%Y%m%d")}.log'
    with open(os.path.join(path, filename), 'w') as logfile:
        logfile.write(f'Alustasime {datetime.now().strftime("%Y%m%d %H:%M:%S")}\n')
        logfile.write(f'{urlvalik}\n')
        for url in url_list:
            if 'http' not in url:
                url = server +  url
            try:
                r = requests.get(url)
                if r.status_code != requests.codes.ok:
                    logfile.write(f'{url} {r.status_code} {len(r.content)}\n')
                    # print(url, r.status_code, len(r.content))
            except:
                logfile.write(f'Viga: {url}\n')
                # print('Viga: ', url)
        logfile.write(f'Vaatasime üle {len(url_list)} linki\n')
        logfile.write(f'Lõpetasime {datetime.now().strftime("%Y%m%d %H:%M:%S")}\n')
            
def main(path, valik):
    server = 'https://valgalinn.ee'
    test_url = ''.join([server, '/test/'])

    testandmed = [
        'test_url_artiklid_id',
        'test_url_isikud_id',
        'test_url_organisatsioonid_id',
        'test_url_objektid_id',
        'test_url_pildid',
        'test_url_viited_id',
        'test_url_artiklid_aasta',
        'test_url_artiklid_kuu',
    ]

    # Küsime kõik serverist valikandmete lingid
    urlvalik = testandmed[valik]
    response = requests.get(f'{test_url}?{urlvalik}')

    # test_andmed = response.json()
    # urls = test_andmed[testandmed[valik]]
    urls = response.json()
    # Testime kõik valitud liigi lingid
    test_urls(path, server, urls, urlvalik)


if __name__ == "__main__":
    # execute only if run as a script
    path = os.path.dirname(sys.argv[0])
    t2na = datetime.now()
    valik = t2na.weekday()
    if len(sys.argv) > 1:
        try:
            valik = int(sys.argv[1])
        except:
            pass
    main(path, valik)