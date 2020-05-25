from datetime import date, datetime, timedelta
import calendar
from calendar import HTMLCalendar
import locale

from django.urls import reverse

from wiki.templatetags.wiki_extras import vkj

KUUL = (
    '',
    'jaanuaril',
    'veebruaril',
    'märtsil',
    'aprillil',
    'mail',
    'juunil',
    'juulil',
    'augustil',
    'septembril',
    'oktoobril',
    'novembril',
    'detsembril',
)

locale.setlocale(locale.LC_ALL, 'et_EE')

def get_date(req_day):
    try:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    except:
        return datetime.today()

def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = 'user_calendar_view_last=' + str(prev_month.year) + '-' + str(prev_month.month)
    return month

def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'user_calendar_view_last=' + str(next_month.year) + '-' + str(next_month.month)
    return month

class Calendar(HTMLCalendar):

    def __init__(self, qs, year=None, month=None):
        self.qs = qs
        self.year = year
        self.month = month
        # self.cssclasses_weekday_head = ["mon", "tue", "wed", "thu", "fri", "sat", "sun w3-red"]
        super(HTMLCalendar, self).__init__()

    def formatday(self, theyear, themonth, theday, events):
        events_per_day = events.filter(dob__day=theday)
        # d = f'<p class="calendar_list"> {events_per_day.count()} </p>'
        kwargs = {
            'year': theyear,
            'month': themonth,
            'day': theday
        }
        if theday != 0:
            link = reverse('wiki:artikkel_day_archive', kwargs=kwargs)
            a_href = f'href={link}'
            class_name = 'day-this-month' # 'calendar_list'
            if events_per_day:
                class_name = ' '.join([class_name, 'day-with-events'])
            a_class = f'class="{class_name}"'
            a_title = f'title="Mis juhtus {theday}. {KUUL[themonth]}?"'
            return f'<td  {a_class}><a {a_href} {a_title}><span>{theday}</span></a></td>'
        return '<td></td>'

    def formatweek(self, theyear, themonth, theweek, events):
        week = ''
        for d in theweek:
            week += self.formatday(theyear, themonth, d, events)
        return f'<tr>{week}</tr>'

    def formatweekheader(self):
        day_abbrs = [f'<th>{d}</th>' for d in iter(calendar.day_abbr)]
        day_abbrs_row = ''.join(day_abbrs)
        return day_abbrs_row

    def formatmonthname(self, theyear, themonth, withyear=True):
        kwargs = {
            'year': theyear,
            # 'month': themonth,
        }
        year_href = reverse('wiki:artikkel_year_archive', kwargs=kwargs)
        year_title = f'Mis juhtus {theyear}?'
        year_link = f'<a href="{year_href}" title="{year_title}" class="month-field">{theyear}</a>'
        kwargs = {
            'year': theyear,
            'month': themonth,
        }
        month_href = reverse('wiki:artikkel_month_archive', kwargs=kwargs)
        month_title = f'Mis juhtus {calendar.month_name[themonth]} {theyear}?'
        month_link = f'<a href="{month_href}" title="{month_title}" class="month-field">{calendar.month_name[themonth]}</a>'
        # monthfield = f'<span <div class="w3-display-topmiddle">{calendar.month_name[themonth]} {theyear}</span>'
        # monthfield = f'{calendar.month_name[themonth]} {theyear}'
        month_field = f'<div class="w3-display-topmiddle">{month_link} {year_link}</div>'
        d = date(theyear, themonth, 1)
        prev_month_action = f"getCalendar('{prev_month(d)}')"
        next_month_action = f"getCalendar('{next_month(d)}')"
        month_prev_button = f'<i class="fa fa-chevron-left w3-display-topleft" onclick="{prev_month_action}"></i>'
        month_next_button = f'<i class="fa fa-chevron-right w3-display-topright" onclick="{next_month_action}"></i>'
        # monthrow = f'{month_prev_button}<span>{monthfield}</span>{month_next_button}'
        return f'<div class="selector">{month_prev_button}{month_field}{month_next_button}</div>'

    def formatmonth(self, withyear=True):
        events = self.qs.filter(dob__year=self.year, dob__month=self.month)
        cal_selector = f'{self.formatmonthname(self.year, self.month, withyear=withyear)}'
        cal_weekheader = f'{self.formatweekheader()}\n'
        # Teeme nii et kuus näidatakse alati viis nädalat
        cal_matrix = []
        for week in self.monthdayscalendar(self.year, self.month):
            cal_matrix.append(week)
        if len(cal_matrix) > 5: # kui kuus nädalat, siis lisame viimase nädala kuupäevad esimesele
            cal_matrix[0] = map(lambda x, y: x + y, cal_matrix[0], cal_matrix[-1])
        if len(cal_matrix) < 5: # kui 1.02 = E ja 28 päeva, siis lisame tühja rea
            cal_matrix.append([0]*7)
        cal_weeks_rows = ''
        for week in range(5):
            cal_weeks_rows += f'{self.formatweek(self.year, self.month, cal_matrix[week], events)}\n'
        # cal_month = f'<div class="days"><table>{cal_weekheader}{cal_weeks_rows}</table></div>'
        cal_month = f'<div class="days">{cal_weeks_rows}</div>'
        cal = f'<div class="calendar"><table>{cal_selector}{cal_month}</table></div>'

        return cal