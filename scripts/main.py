import requests
import time
import os
import sys
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import DuplicateKeyError

RED = '\033[31m'
GREEN = '\033[32m'
MAGENTA = '\033[35m'
CYAN = '\033[36m'
RESET = '\033[0m'

"""
Post Data from /.json

data["author"] => author
data["url"] => url
data["created"] => created
data["link_flair_text"] => tag
data["title"] => title
data["selftext"] => body

"""
class RedditData:
    def __init__(self, author, created, tag, title, body, url):
        self.author = author
        self.created = created
        self.tag = tag
        self.title = title
        self.body = body
        self.url = url

"""
Database Reset & Index Creation
"""
def mongodb_setup(mongodb_client):
    if not mongodb_client:
        print(RED + "MongoDB Client Not Found. Quitting Application." + RESET)
        sys.exit(1)
    
    print("Setting up MongoDB Database Collections and Indexes...")
    
    mdb_db = os.environ.get("MONGO_DATABASE")
    mdb_coll = os.environ.get("MONGO_COLLECTION")
    database = client[mdb_db]
    collection = database[mdb_coll]
    
    # Drop all data in collections
    collection.delete_many({})
    
    # Create Index on Author and Created time.
    collection.create_index( { "author": 1, "created": 1 }, unique=True )

"""
MongoDB Connection Handler
"""
def connect_to_mongodb():
    cluster = os.environ.get("MONGO_CLUSTER")
    un = os.environ.get("MONGO_USERNAME")
    pw = os.environ.get("MONGO_PASSWORD")
    
    uri = f"mongodb+srv://{un}:{pw}@{cluster}"
    
    client = MongoClient(uri, server_api=ServerApi('1'))
    
    try:
        client.admin.command('ping')
        print(GREEN + "Pinged your deployment. You successfully connected to MongoDB!" + RESET)
        
        return client
    except Exception as e:
        print(RED + f"Error connecting to MongoDB. Quitting Application with Error: {e}" + RESET)
        sys.exit(1)

def pause_exec(interval):
    time.sleep(interval)

"""
Read through the returned Post JSON
Map specific data points and save to MongoDB
"""
def process_json_to_mongodb(json_data, mongodb_client = None):
    if not mongodb_client:
        print(RED + "MongoDB Client Not Found. Quitting Application." + RESET)
        sys.exit(1)
    
    mdb_db = os.environ.get("MONGO_DATABASE")
    mdb_coll = os.environ.get("MONGO_COLLECTION")
    database = mongodb_client[mdb_db]
    collection = database[mdb_coll]
    
    insert_count = 0
    duplicate_count = 0
    failed_count = 0
    for child in json_data['data']['children']:
        # We only want text posts
        if child["data"]["selftext"]:
            post = RedditData(
                child["data"]["author"],
                child["data"]["created"],
                child["data"]["link_flair_text"],
                child["data"]["title"],
                child["data"]["selftext"],
                child["data"]["url"]
            )
            
            try:
                result = collection.insert_one(vars(post))
            
                if result.inserted_id:
                    insert_count += 1
            except DuplicateKeyError as e:
                duplicate_count += 1
            except Exception as e:
                failed_count += 1
                 
            
    print(GREEN + f"Saved to MongoDB: {insert_count} Posts. Duplicated: {duplicate_count}, Failed: {failed_count}" + RESET)
        
"""
Handle GET Requests to the Reddit Page
Retries a max of 3 times during Rate Limiting before exiting
"""
def fetch_reddit_posts(after = "", mongodb_client = None):
    if not mongodb_client:
        print(RED + "MongoDB Client Not Found. Quitting Application." + RESET)
        sys.exit(1)
    
    post_limit = 100
    reddit_page = os.environ.get("REDDIT_PAGE")
    url = f"{reddit_page}/.json?limit={post_limit}&after={after}"

    user_agent = os.environ.get("USERAGENT")
    headers = {
        "User-Agent": user_agent
    }

    try:
        retry = 0
        retry_limit = 3
        retry_pause_interval = 60
        
        while retry < retry_limit:
            response = requests.get(url, headers, timeout=5)
            
            if response.status_code == 429:
                print(RED + f"#### Rate Limit Reached: Status Code {response.status_code} - Displaying Response Headers ####" + RESET)
                for header_name, header_value in response.headers.items():
                    print(RED + f"{header_name}: {header_value}" + RESET)
                    
                retry += 1
                if retry == retry_limit:
                    response.raise_for_status()
                    break 
                
                print(CYAN + f"Pausing for {retry_pause_interval} seconds then retrying GET Request..." + RESET)
                pause_exec(retry_pause_interval)
                
            elif response.status_code == 200:
                print(GREEN + f"Success {response.status_code} retrieving posts!" + RESET)
                json_data = response.json()
                process_json_to_mongodb(json_data, mongodb_client)
                
                next_after = json_data['data']['after']
                return next_after
            
            else:
                print(RED + f"Unhandled Error: {response.status_code}" + RESET)
                response.raise_for_status()
                break
        
    except requests.exceptions.RequestException as e:
        print(RED + f"Error fetching data: {e}. Closing Application." + RESET)
        sys.exit(1)

"""
Main loop-de-doo for managing pages to fetch
"""
def loop(mongodb_client):
    if not mongodb_client:
        print(RED + "MongoDB Client Not Found. Quitting Application." + RESET)
        sys.exit(1)
    
    # 10 is apparently the max pagination depth we can go to retrieving 100 posts
    # Pagination may be higher if you set post amount less.
    fetch_pages = 10
    
    # Time inbetween fetches
    interval = 30
    
    estimated_time = ((fetch_pages * interval) + 180) / 60 # Lil extra buffer for Rate Limiting
    print(CYAN + f"Estimated time to completion: {estimated_time} minutes." + RESET)

    after = ""
    for i in range(fetch_pages):
        iteration = i+1
        print(GREEN + f"Fetching posts from next page: {after} -- Current Fetch Iteration: {iteration} / {fetch_pages}" + RESET)
        
        after = fetch_reddit_posts(after, mongodb_client)  
        
        print(CYAN + f"Pausing for {interval} seconds." + RESET)
        pause_exec(interval)
    
if __name__ == "__main__":
    
    client = connect_to_mongodb()
    
    # Uncomment to clear database data or initially create index
    #mongodb_setup(client)
    
    loop(client)
    
    client.close()
    