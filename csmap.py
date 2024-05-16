import requests
import json
import itertools
import sys
import signal
import os
import random
import string
import re
import asyncio
import aiohttp
from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError

csmap_version = "2.1pub"

# Global variable to keep track of current state
current_code = None
base_url = "https://comicstud.io/c/"
json_filename = "valid_urls.json"

def generate_urls(start, end):
    charset = 'abcdefghijklmnopqrstuvwxyz'

    def increment_string(s):
        lpart = list(s)
        for i in range(len(lpart) - 1, -1, -1):
            if lpart[i] != 'z':
                lpart[i] = charset[charset.index(lpart[i]) + 1]
                return ''.join(lpart[:i + 1]) + 'a' * (len(lpart) - i - 1)
        # print(f"[DEBUG] lpart: {lpart}")
        return None  # If we can't increment further, return None

    current = start
    while current != end:
        yield current
        current = increment_string(current)
        if current is None:
            break
    yield end
    
def clean_final_url(final_url):
    # Remove the .png extension
    final_url = re.sub(r"\.png$", "", final_url)
    # Extract the last 10 characters
    cleaned_url = final_url[-10:]
    return cleaned_url

async def check_url_status(session, url, user_agent):
    headers = {'User-Agent': user_agent}
    try:
        async with session.get(url, headers=headers, allow_redirects=True) as response:
            final_url = str(response.url)
            # print(f"[DEBUG] response: {response}")
            if response.status == 200 and final_url != url and 'https://cdn.comic.studio/comics' in final_url:
                print(f"Valid:   {url} | {final_url}")
                return 1, final_url
            elif response.status == 403:
                print(f"Special: {url} | {final_url}")
                return 2, final_url
            else:
                print(f"Invalid: {url} | {final_url}")
                return 0, final_url
    except ClientError:
        print(f"Error occured.")
        return 0, None

def save_to_json(valid_urls, filename=json_filename):
    with open(filename, 'w') as json_file:
        json.dump(valid_urls, json_file, indent=4)

def save_state(state, filename):
    with open(filename, 'w') as f:
        json.dump(state, f)

def load_state(filename):
    with open(filename, 'r') as f:
        return json.load(f)

def signal_handler(sig, frame):
    # Save current state to a file with random 32-character hex name
    temp_filename = ''.join(random.choices(string.hexdigits, k=32)).lower() + '.csmaptmp'
    state = {
        "current_code": current_code,
        "start_range": range1,
        "end_range": range2
    }
    save_state(state, temp_filename)
    print(f"\nInterrupted! State saved to {temp_filename}")
    sys.exit(0)

async def main():
    global current_code, range1, range2

    signal.signal(signal.SIGINT, signal_handler)

    if len(sys.argv) == 2 and sys.argv[1].startswith('-c'):
        # Resume from saved state
        temp_filename = sys.argv[1][2:]
        if not os.path.isfile(temp_filename):
            print(f"Temporary state file {temp_filename} does not exist.")
            sys.exit(1)
        state = load_state(temp_filename)
        current_code = state["current_code"]
        range1 = state["start_range"]
        range2 = state["end_range"]
        os.remove(temp_filename)
    elif len(sys.argv) >= 3:
        # New execution
        range1, range2 = sys.argv[1], sys.argv[2]
        if len(range1) != 10 or len(range2) != 10:
            print("Both ranges must be exactly 10 characters long.")
            sys.exit(1)
        current_code = None
    else:
        print("Usage: python script.py [param]")
        print("Command param:")
        print("[range 1, must be 10 char] [range 2, must be 10 char] (required, except restoring state)")
        print("-t [threads] (optional)")
        print("-ua [user agent] (optional)")
        print("-c <saved state file>.csmaptmp (required, restore only)")
        sys.exit(1)

    threads = 10
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    # Parse additional arguments
    for i in range(3, len(sys.argv), 2):
        if sys.argv[i] in ("-t", "--threads"):
            threads = int(sys.argv[i + 1])
        elif sys.argv[i] in ("-ua", "--user-agent"):
            user_agent = sys.argv[i + 1]

    if os.path.isfile(json_filename):
        with open(json_filename, 'r') as f:
            valid_urls = json.load(f)
    else:
        valid_urls = {}

    if current_code:
        skip = True
    else:
        skip = False

    async with aiohttp.ClientSession() as session:
        url_queue = asyncio.Queue()

        # Enqueue all URLs to be checked
        for code in generate_urls(range1, range2):
            if skip:
                if code == current_code:
                    skip = False
                continue
            await url_queue.put(code)

        async def worker():
            while not url_queue.empty():
                code = await url_queue.get()
                global current_code
                current_code = code
                url = base_url + code
                status, final_url = await check_url_status(session, url, user_agent)
                if status in [1, 2]:
                    cleaned_url = clean_final_url(final_url)
                    valid_urls[cleaned_url] = status
                    save_to_json(valid_urls)  # Save immediately when a valid URL is found

        # Create and run workers
        tasks = []
        for _ in range(threads):
            task = asyncio.create_task(worker())
            tasks.append(task)

        await asyncio.gather(*tasks)

    save_to_json(valid_urls)  # Final save to ensure all valid URLs are saved

if __name__ == "__main__":
    os.system("title CSMC - CSmap")
    print(f"CSmap {csmap_version}")
    print("by Bang1338 and AuLeStub")
    print("for Comic Studio Modding Council\n")
    print("DO NOT USE IT FOR ILLEGAL PURPOSE!")
    print("This project has been approved by Bang1338 for publishing on GitHub.\n")
    print("Heavily inspired from nmap - the Network Mapper\n")
    asyncio.run(main())