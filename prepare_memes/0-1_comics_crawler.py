#!/usr/bin/env python3
'''
Author : allieus
Copied from : https://gist.github.com/allieus/13c1a80ef5648c2b9b112e1c58f9727b
'''
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import requests
from bs4 import BeautifulSoup


base_dir = "downloaded"

def crawl_naver_webtoon(episode_url, no):
    html = requests.get(episode_url).text
    soup = BeautifulSoup(html, 'html.parser')

    for img_tag in soup.select('.wt_viewer img'):
        url = img_tag['src']
        base_path = os.path.join(os.path.dirname(__file__), base_dir, f'{no:03d}')
        file_path = os.path.join(base_path, os.path.basename(url))

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        print(file_path)
        headers = {'Referer': episode_url}
        image_file_data = requests.get(url, headers=headers).content
        open(file_path, 'wb').write(image_file_data)

    print(f"{no} completed")


if __name__ == '__main__':
  for no in range(1, 160):
    episode_url = 'https://comic.naver.com/webtoon/detail?titleId=103759&no=' + str(no)
    crawl_naver_webtoon(episode_url, no)
