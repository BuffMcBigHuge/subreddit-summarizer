# Reddit Summarizer

A script that uses PRAW and OpenAI to analyze a subreddit and identify pain points of users.

## Requirements
An [OpenAI Key](https://platform.openai.com/api-keys) and [Reddit App](https://old.reddit.com/prefs/apps/).
```
export REDDIT_CLIENT_ID = ** your reddit client key **
export REDDIT_CLIENT_SECRET = ** your reddit client secret **
export REDDIT_USER_AGENT = ** your reddit user agent **
export OPEN_API_KEY = ** your openai key **
```

You can adjust any of the variables in reddit.py:
```
POST_LIMIT=100 # Maximum number of posts to retrieve per subreddit
TOKENS_PER_REQUEST=8000 # Maximum number of tokens to send to OpenAI per request
MAX_REQUESTS=10 # Maximum number of requests to make to OpenAI per subreddit
DELAY_BETWEEN_REQUESTS=0 # Wait time in seconds between OpenAI requests
DELAY_BETWEEN_SUBREDDITS=60 # Wait time in seconds between subreddit requests
USE_GPT4 = False
INSTRUCT_SUMMARIZE = 'Identify and summarize the main pain points discussed in the following subreddit data:'
INSTRUCT_SUMMARIZE_GPT4 = 'Please summarize this data further. I want to know the business opportunities:'
SUBREDDITS = [
    'futurology',
]
```

# Startup

```
pip install requirements.txt
python reddit.py
```