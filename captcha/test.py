import re
import json
import traceback
from pathlib import Path

from imgcat import imgcat

from lib import (
    guess,
    get_tess_api_old,
    get_tess_api_new,
    get_debug_info
)

def show_debug_info():
    debug_info = get_debug_info()
    print('main img')
    imgcat(debug_info['imgs']['main'])
    print('thresh img')
    imgcat(debug_info['imgs']['thresh'])
    print('dilated img')
    imgcat(debug_info['imgs']['dilated'])
    for i, b in enumerate(debug_info['bboxes']):
        print(b)
        imgcat(debug_info['imgs']['pieces'][i])
    print(debug_info['responder'])



if __name__ == '__main__':
    with open('data/truth.json') as f:
        truth_data = json.load(f)

    success = 0
    total_count = len(truth_data)
    curr_count = 0

    tess_api_old = get_tess_api_old()
    tess_api_new = get_tess_api_new()

    for filename, value in truth_data.items():
        print(f'testing file: {filename}')
        label_filename = filename.replace('imgs', 'labels').replace('.gif', '.txt')
        label_type = Path(label_filename).read_text()
        print(label_type)
        img_content = Path(filename).read_bytes()
        try:
            guessed = guess(tess_api_new, tess_api_old, img_content, label_type)
        except Exception as ex:
            traceback.print_exception(ex)
            guessed = 'EXCEPTION'
        curr_count += 1
        outcome = 'FAILED'
        if guessed == value:
            outcome = 'SUCCESS'
            success += 1

        if outcome != 'SUCCESS':
            show_debug_info()
        print(f'{curr_count:2}/{total_count:2} {guessed:6} {outcome:7} {success:2}/{curr_count}')

