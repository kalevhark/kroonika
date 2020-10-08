from datetime import datetime
import json

AASTA = 2020
# teams = dict()

# results = dict()
games = dict()

def add_html_tag(content, add_tag='div', add_class=None):
    add_class_str = f' class="{add_class}"' if add_class else ''
    return f'<{add_tag}{add_class_str}>{content}</{add_tag}>'

def reverse_tuple(tuple):
    return (tuple[1], tuple[0])


def file2json(aasta=AASTA):
    days = dict()
    with open(f'vp{aasta}.txt', 'r', encoding='utf-8') as f:
        read = f.readlines()
        for rida in read:
            splitid = rida.split(';')
            if rida.startswith('D'):
                kp = [int(split) for split in splitid[1].split('.')]
                p2ev = datetime(AASTA, kp[1], kp[0])
                # p2ev_string = p2ev.strftime('%Y-%m-%d')
                days[p2ev] = {
                    'teams': dict(),
                    'games': dict()
                    }
            elif rida.startswith('T'):
                team = int(splitid[1])
                days[p2ev]['teams'][team] = [m2ngija.strip() for m2ngija in splitid[2].split(',')]
            elif rida.startswith('M'):
                team1, team2 = [int(team) for team in splitid[1].split('-')]
                scor1, scor2 = [int(scor) for scor in splitid[2].split(':')]
                days[p2ev]['games'][(team1, team2)] = (scor1, scor2)
    return days
    
def make_tables(days):
    for day in days:
        # Loome mängutabeli
        teams = len(days[day]['teams'])
        games = len(days[day]['games'])
        print(day, teams, games, end=' - ')
        # Kontroll
        if games == sum(range(1, teams)):
            print('OK')
        else:
            print('NOK')
        read = []
        for v in range(1, teams+1):
            rida = []
            for h in range(1, teams+1):
                if v == h:
                    scor = ('')
                elif h > v:
                    scor = days[day]['games'][v, h]
                elif h < v:
                    scor = reverse_tuple(days[day]['games'][h, v])
                rida.append(scor)
            read.append(rida)
        days[day]['table'] = read
    return days

def make_days2html(days):
    def result(el):
        if el:
            return f'{el[0]}:{el[1]}'
        else:
            return '---'
    html_string = ''
    for key in days.keys():
        
        # Päeva pealkiri
        date_string = key.strftime('%d.%m')
        print(date_string)
        # html_string_day = f'<p>{date_string}</p>'
        html_string_day = ''
        # Päeva tabel
        html_string_day_table = ''
        tiimid = days[key]['teams']
        tiime = len(tiimid)
        # Päeva tabeli pealdis
        html_string_day_table_head = add_html_tag(date_string, add_tag='th')
        for tiim in range(1, len(tiimid)+1):
            html_string_day_table_head += add_html_tag(str(tiim), add_tag='th')
        html_string_day_table = add_html_tag(
            html_string_day_table_head,
            add_tag='tr'
            )
        print('Tiim', [tiim for tiim in range(1, len(tiimid)+1)])
        # Päeva tabeli sisu
        for k, v in tiimid.items():
            table = days[key]['table']
            html_string_day_table_row = add_html_tag(
                f'{k} {", ".join(v)}',
                add_tag='td'
                )
            for el in table[k-1]:
                html_string_day_table_row += add_html_tag(result(el), add_tag='td')
            html_string_day_table += add_html_tag(
                html_string_day_table_row,
                add_tag='tr'
                )
            print(k, ','.join(v), [result(el) for el in table[k-1]])

        html_string_day += add_html_tag(
            html_string_day_table,
            add_tag='table',
            add_class='w3-table-all'
            )
        
        html_string += add_html_tag(
            html_string_day,
            add_tag='div',
            add_class='day')
    return html_string

def make_tops2html(name, top_data):
    html_string = add_html_tag(name, 'th') + add_html_tag('', 'th')
    html_string = add_html_tag(html_string, 'tr')    
    for k, v in top_data.items():
        html_string_day_table_row = f'<td>{k}</td><td style="text-align:right;">{v}</td>'
        html_string += add_html_tag(html_string_day_table_row, 'tr')
    # ... siit edasi teha
    html_string = add_html_tag(
        html_string,
        add_tag='table',
        add_class='w3-table-all'
        )
    return html_string

def player_results(days):
    m2ngijad = dict()
    for day in days:
        # Leiame mängude tulemused
        for team in days[day]['teams']:
            games = 0
            wins = 0
            for game, scor in days[day]['games'].items():
                if team in game:
                    wins  += scor[game.index(team)]
                    games += scor[0] + scor[1]
            # Lisame mängija tulemused
            for m2ngija in days[day]['teams'][team]:
                if m2ngija not in m2ngijad:
                    m2ngijad[m2ngija] = dict()
                m2ngijad[m2ngija][day] = {'games': games, 'wins': wins}
    return m2ngijad

# Loeme andmed
days_data = file2json()
days = make_tables(days_data)

# Teeme koodtabeli mängjatest
m2ngijad = player_results(days)

for m2ngija in m2ngijad:
    times_count = len(m2ngijad[m2ngija])
    game_count = 0
    win_count = 0
    for day in m2ngijad[m2ngija]:
        game_count += m2ngijad[m2ngija][day]['games']
        win_count += m2ngijad[m2ngija][day]['wins']
    m2ngijad[m2ngija]['total'] = {
        'times': times_count,
        'games': game_count,
        'wins': win_count
        }
    print(m2ngija, times_count, game_count, win_count, round(win_count/game_count, 1))
    
# Enim osalenud
enim_osalenud = {
    k: v['total']['times']
    for k, v
    in sorted(
        m2ngijad.items(),
        key=lambda item: item[1]['total']['times'],
        reverse=True
        )
    }
# Enim võidetud geime
enim_geime = {
    k: v['total']['games']
    for k, v
    in sorted(
        m2ngijad.items(),
        key=lambda item: item[1]['total']['games'],
        reverse=True
        )
    }

# MVP
enim_MVP = {
    k: f"{round(v['total']['wins']/v['total']['games'], 2):.2f}"
    for k, v
    in sorted(
        m2ngijad.items(),
        key=lambda item: (item[1]['total']['wins']/item[1]['total']['games']),
        reverse=True
        )
    }

html_string_top_osalemisi = make_tops2html('Kordi osalenud', enim_osalenud)
html_string_top_geimiv6ite = make_tops2html('Mängitud geime', enim_geime)
html_string_top_MVP = make_tops2html('MVP', enim_MVP)

html_string_days = make_days2html(days)
with open('vp2020.html', 'w', encoding='utf8') as f:
    f.write(
        add_html_tag(
            html_string_top_osalemisi,
            add_tag='div'
            )
        )
    f.write(
        add_html_tag(
            html_string_top_geimiv6ite,
            add_tag='div'
            )
        )
    f.write(
        add_html_tag(
            html_string_top_MVP,
            add_tag='div'
            )
        )
    f.write(
        add_html_tag(
            html_string_days,
            add_tag='div'
            )
        )
    
# open json file for writing
##with open('vp2020.json', 'w') as f:
##    json.dump(data, f, indent=4)
css_string = '<link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">'
