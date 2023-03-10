import glob
import json
import shutil
from pathlib import Path
from PIL import Image
from imgcat import imgcat

truth_file = 'data/truth.json'
if not Path(truth_file).exists():
    with open(truth_file, 'w') as f:
        f.write('{}')

with open(truth_file, 'r') as f:
    truth_data = json.load(f)

filenames = glob.glob('data/imgs/*.gif')

for filename in filenames:
    if filename in truth_data:
        continue
    label_file = filename.replace('imgs', 'labels').replace('gif', 'txt')
    prompt = Path(label_file).read_text()
    print(f'annotating {filename}')
    img = Image.open(filename)
    imgcat(img)
    inp = input(f'{prompt}:')
    val = inp.strip()
    truth_data[filename] = val

#TODO: this should have been an incremental jsonl dump
with open(f'{truth_file}.new', 'w') as f:
    json.dump(truth_data, f, indent = 2)

shutil.move(f'{truth_file}.new', truth_file)
