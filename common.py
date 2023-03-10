from urllib.parse import urljoin
from bs4 import BeautifulSoup

MAIN_URL = 'www.indiapost.gov.in'
TRACKING_URL = "https://www.indiapost.gov.in/_layouts/15/DOP.Portal.Tracking/TrackConsignment.aspx"

class CaptchaFailedException(Exception):
    pass

def get_main_tracking_page(session):
    resp = session.get(TRACKING_URL)
    if not resp.ok:
        raise Exception(f'Unable to get page: {TRACKING_URL}, {resp.status_code=}')

    soup = BeautifulSoup(resp.text, 'html.parser')


def get_data_from_post(resp_text):

    panel_label = '|updatePanel|ctl00_PlaceHolderMain_ucNewLegacyControl_upnlTrackConsignment|'
    idx = resp_text.find(panel_label)
    str_len = int(resp_text[:idx].split('|')[-1])
    count = 0
    idx = idx + len(panel_label)
    start_idx = idx
    while count < str_len:
        if resp_text[idx] == '\n':
            count += 2
        else:
            count += 1
        idx += 1
    end_idx = idx
    html = resp_text[start_idx:end_idx]

    pieces = resp_text[end_idx+1:].split('|')
    idx = 0
    base_form_data = {}
    while idx < len(pieces):
        if pieces[idx] != 'hiddenField':
            idx += 1
            continue
        idx += 1
        key = pieces[idx]
        idx += 1
        val = pieces[idx]
        #print(key)
        base_form_data[key] = val
        idx += 1
    return html, base_form_data


def get_captcha(soup, session):

    captcha_div = soup.find('div', { 'id': 'ctl00_PlaceHolderMain_ucNewLegacyControl_divcaptcha' })

    captcha_label = captcha_div.find('span', {'id': 'captcha_label'}).text.strip()

    captcha_container = captcha_div.find('div', {'id': 'captcha_container'})
    captcha_img_url_rel = captcha_container.find('img').attrs['src']
    captcha_img_url = urljoin(TRACKING_URL, captcha_img_url_rel)

    cresp = session.get(captcha_img_url)
    if not cresp.ok:
        raise Exception(f'Unable to get page: {captcha_img_url}, {cresp.status_code=}')

    gif_file_contents = cresp.content

    return gif_file_contents, captcha_label


def get_reload_form_data_from_page(soup, has_form=False):
    if has_form:
        form = soup.find('form')
    else:
        form = soup
    inputs = form.find_all('input')
    form_data = {}
    for inp in inputs:
        inp_name = inp.attrs.get('name', None)
        if inp_name is None:
            continue
        form_data[inp_name] = inp.attrs.get('value', '')

    form_data['__ASYNC_POST'] = 'true'
    form_data['__EVENTARGUMENT'] = ''
    form_data['__EVENTTARGET'] = ''
    form_data['__LASTFOCUS'] = ''

    # TODO: check these magic values
    form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$ucCaptcha1$imgbtnCaptcha.x'] = '6'
    form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$ucCaptcha1$imgbtnCaptcha.y'] = '11'

    form_data['ctl00$ScriptManager'] = 'ctl00$PlaceHolderMain$ucNewLegacyControl$upcaptcha|ctl00$PlaceHolderMain$ucNewLegacyControl$ucCaptcha1$imgbtnCaptcha'

    del form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$btnReset']
    del form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$btnSearch']
    del form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$ucCaptcha1$imgbtnCaptcha']

    return form_data

def get_tracking_form_data_from_page(soup, tracker_id):
    inputs = soup.find_all('input')
    form_data = {}
    for inp in inputs:
        inp_name = inp.attrs.get('name', None)
        if inp_name is None:
            continue
        form_data[inp_name] = inp.attrs.get('value', '')

    form_data['__ASYNC_POST'] = 'true'
    form_data['__EVENTARGUMENT'] = ''
    form_data['__EVENTTARGET'] = ''
    form_data['__LASTFOCUS'] = ''
    form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$txtOrignlPgTranNo'] = tracker_id
    form_data['ctl00$ScriptManager'] = 'ctl00$PlaceHolderMain$ucNewLegacyControl$upnlTrackConsignment|ctl00$PlaceHolderMain$ucNewLegacyControl$btnSearch'

    del form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$btnReset']
    del form_data['ctl00$PlaceHolderMain$ucNewLegacyControl$ucCaptcha1$imgbtnCaptcha']

    return form_data


def reload_captcha(reload_form_data, session):
    resp = session.post(TRACKING_URL,
                        data=reload_form_data,
                        headers={
                            'User-Agent': 'Mozilla',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-MicrosoftAjax': 'Delta=true',
                        })
    if not resp.ok:
        raise Exception(f'Unable to reload captcha: {TRACKING_URL}, {resp.status_code=} {reload_form_data=}')

    html, form_data = get_data_from_post(resp.text)
    return html, form_data


def get_tracking_details(track_form_data, session):
    resp = session.post(TRACKING_URL,
                        data=track_form_data,
                        headers={
                            'User-Agent': 'Mozilla',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                            'X-MicrosoftAjax': 'Delta=true',
                        })
    if not resp.ok:
        raise Exception(f'Unable to make tracking call: {TRACKING_URL}, {resp.status_code=} {track_form_data=}')
    html, form_data = get_data_from_post(resp.text)

    soup = BeautifulSoup(html, 'html.parser')

    captcha_err_div = soup.find('div', { 'id': 'captcha_errormsg' })
    if captcha_err_div is not None:
        raise CaptchaFailedException()

    summary_table = soup.find('table', { 'id': 'ctl00_PlaceHolderMain_ucNewLegacyControl_gvTrckMailArticleDtlsOER' })
    summary_data = parse_table(summary_table)

    status_text = soup.find('span', {'id': 'ctl00_PlaceHolderMain_ucNewLegacyControl_lblMailArticleCurrentStatusOER'}).text.strip()
    status_text = status_text.replace('Current Status :', '').strip()

    event_table = soup.find('table', { 'id': 'ctl00_PlaceHolderMain_ucNewLegacyControl_gvTrckMailArticleEvntOER' })
    event_data = parse_table(event_table)

    return status_text, summary_data, event_data


def parse_table(table):
    val_dicts = []
    keys = []
    trs = table.find_all('tr', recursive=False)
    if len(trs) < 2:
        return []
    header_tr = trs[0]
    ths = header_tr.find_all('th', recursive=False)
    keys = [th.text.strip() for th in ths]
    for tr in trs[1:]:
        tds = tr.find_all('td', recursive=False)
        vals = [td.text.strip() for td in tds]
        val_dict = dict(zip(keys, vals))
        val_dicts.append(val_dict)
    return val_dicts
