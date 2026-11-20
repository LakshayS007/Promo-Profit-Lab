"""Copies the 84.51° Complete Journey tables (shipped as Parquet inside the completejourney-py package) into data/raw/.
Usage: pip install completejourney-py && python data/get_data.py"""
import importlib.resources as r, shutil, os
os.makedirs('data/raw', exist_ok=True)
src = r.files('completejourney_py').joinpath('data')
for f in src.iterdir():
    if f.name.endswith('.parquet'):
        with r.as_file(f) as p: shutil.copy(p, f'data/raw/{f.name}')
        print('copied', f.name)
