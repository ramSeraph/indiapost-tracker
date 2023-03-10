import requests
from bs4 import BeautifulSoup
from pathlib import Path
from pprint import pprint

from ..common import (
    get_main_tracking_page,
    get_data_from_post,
    get_captcha,
    get_reload_form_data_from_page,
    reload_captcha
)



"""
    # hack for truncated post responses if they show up
    temp_file = data_dir / f'{name}.wip/{dist_name}.wip/{pno}.txt'
    temp_file.write_text(resp.text)
    resp_text = temp_file.read_text()
    temp_file.unlink()
"""



def write_files(gif_file_contents, captcha_label):

    data_dir = Path('data')
    imgs_dir = data_dir / 'imgs'
    labels_dir = data_dir / 'labels'

    imgs_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    counter_file = data_dir / 'counter.txt'
    if not counter_file.exists():
        counter_file.write_text('0')
    counter = int(counter_file.read_text())

    label_file = labels_dir / f'{counter}.txt'
    label_file.write_text(captcha_label)

    captcha_file = imgs_dir / f'{counter}.gif'
    captcha_file.write_bytes(gif_file_contents)
    counter_file.write_text(f'{counter + 1}')


if __name__ == '__main__':

    count = 0
    print('getting main page')
    session = requests.session()
    soup = get_main_tracking_page(session)
    print(f'getting captcha data: {count}')
    img_content, label = get_captcha(soup, session)
    write_files(img_content, label)
    reload_form_data = get_reload_form_data_from_page(soup, has_form=True)
    count += 1

    while count < 100:
        print('reloading captcha')
        html, form_data = reload_captcha(reload_form_data, session)
        soup = BeautifulSoup(html, 'html.parser')
        print(f'getting captcha data: {count}')
        img_content, label = get_captcha(soup, session)
        write_files(img_content, label)
        reload_form_data = get_reload_form_data_from_page(soup)
        reload_form_data.update(form_data)
        count += 1


