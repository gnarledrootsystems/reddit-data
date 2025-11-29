# Reddit Page Post Scraper

Given a page on reddit (`https://www.reddit.com/r/{page}`), scrape the `/.json` post data up to 1000 posts and save it to your MongoDB Cluster.

## Project Setup

1. Create your MongoDB Database and Collection (Cloud or Local)
2. Rename `example.app.env` to `app.env`
3. Start adding the relevant variables
4. For the `USERAGENT`, add something along the lines of `Platform:Reddit_Data:v0.0.1 (by u/RedditUsername)`
5. For the initial run, in `/scripts/main.py` uncomment the `#mongodb_setup(client)` at the bottom of the script for your first run to setup the index in mongodb.
6. Run the docker compose commands to start the project
7. `docker compose build` or `docker compose build --no-cache`
8. `docker compose up` or `docker compose up -d`
9. To stop, press `ctrl-c` or `docker compose stop` or `docker compose down`

The Rate Limiting reported in the Headers will be 100 calls every 10 minutes or so. This unfortunately isn't accurate as they will likely rate limit you in other ways, like ip based, so there is a high chance running the script will work and then return Status Code `429` Rate Limit. The script will retry the same page 3 times before quitting. Then you might need to wait for a time and try again.

As long as you comment out `#mongodb_setup(client)` after the initial run, the post inserts won't duplicate or override due to the index set.
