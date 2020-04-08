#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from concurrent.futures import ThreadPoolExecutor
from itertools import count, cycle, repeat
from pathlib import Path

from cachecontrol import CacheControl
from requests import Session
from tqdm import tqdm

from utils import dump, get, get_proxies, get_book_id, get_headers, load, mkdirs, read, sanitize_file, write

NB_RETRIES = 10

def main():
    # create dirs
    root_dir = Path(__file__).resolve().parents[1]
    data_dir = root_dir / 'data'
    dump_dir = root_dir / 'dump'
    mkdirs(data_dir, dump_dir)
    gold_proxies = [
        'https://51.158.186.242:8811',
    ]
    proxies = [
    ]
    print(proxies)

    proxy_idx = 0
    while True:
        # load book_download_urls
        book_download_urls = read(root_dir / 'book_download_urls.txt', 'r').splitlines()

        # remove any books that have already been downloaded
        book_download_urls = [url for url in book_download_urls if not (data_dir / f'{get_book_id(url)}.txt').exists()]

        if book_download_urls:
            # keep only the first 500 (as smashwords blocks the IP-address after 500 requests)
            book_download_urls = book_download_urls[:48]

            # get headers (user-agents)
            headers = get_headers(root_dir / 'user-agents.txt')

            # initialize cache-controlled session
            session = CacheControl(Session())

            # get the books (concurrently)
            with ThreadPoolExecutor(max_workers=6) as executor:
                for nb_retry in count(1):
                    # break if all book_download_urls successful
                    if not book_download_urls:
                        break

                    # break if max number of retries exceeded
                    # if nb_retry > NB_RETRIES:
                        # print(f'Could not download {len(book_download_urls)} books after {NB_RETRIES} retries.')
                        # break

                    cur_proxy = proxies[proxy_idx]
                    print(f'current proxy: {cur_proxy} (#{proxy_idx})')

                    # maintain a list of failed downloads (for future retries)
                    failed_book_download_urls = []
                    nr_books = len(book_download_urls)

                    # get the book_responses
                    book_responses = list(tqdm(executor.map(get, book_download_urls, repeat(session), cycle(headers), repeat(cur_proxy)), total=len(book_download_urls), desc='Getting books'))

                    # dump the book_responses
                    dump(book_responses, 'book_responses.pkl')

                    for book_url, book_r in zip(book_download_urls, book_responses):
                        if book_r is not None:
                            if book_r.status_code == 200:
                                book_r.encoding = 'utf-8'

                                # write the content to disk
                                write(book_r.content, data_dir / f'{get_book_id(book_url)}.txt')
                            else:
                                failed_book_download_urls.append(book_url)
                                print(f'Request failed for {book_url}: status code [{book_r.status_code}]')

                    nr_failure = len(failed_book_download_urls)
                    book_download_urls = failed_book_download_urls

                    if nr_failure == nr_books:
                        proxy_idx += 1


if __name__ == '__main__':
    main()
