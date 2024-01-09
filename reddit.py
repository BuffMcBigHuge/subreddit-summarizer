# reddit.py

import asyncpraw
from openai import OpenAI
import tiktoken
import os
import asyncio

REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET')
REDDIT_USER_AGENT = os.getenv('REDDIT_USER_AGENT')
OPEN_API_KEY = os.getenv('OPEN_API_KEY')

# Check if any of the environment variables are missing
if not all([REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, OPEN_API_KEY]):
    raise EnvironmentError('Missing one or more required environment variables (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, OPEN_API_KEY)')

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

if not SUBREDDITS:
    raise ValueError("Subreddits list is empty.")

# Setup PRAW with your Reddit API credentials
reddit = asyncpraw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# Setup OpenAI API key
client = OpenAI(api_key=OPEN_API_KEY)

async def get_subreddit_data(subreddit_name, post_limit=100):
    print(f">>>>> Getting subreddit data for /r/{subreddit_name}")

    subreddit = await reddit.subreddit(subreddit_name)
    data = []

    async for submission in subreddit.hot(limit=post_limit):
        # Collect submission data

        submission_data = {
            'title': submission.title,
            'selftext': submission.selftext,
            'comments': []
        }

        # Collect comments data
        submission.comment_sort = "new"
        await submission.load()
        comments = submission.comments.list()
        
        for comment in comments:
            if hasattr(comment, 'body'):
                submission_data['comments'].append(comment.body)

        # Append the post data to the list
        data.append(submission_data)
    
    print(f">>>>> Found {len(data)} posts")
    
    return data

async def openai_analysis(instruct, chunk, model='gpt-3.5-turbo-16k'):
    print(f">>>>> Calling OpenAI API")

    stream = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user", 
                "content": f"{instruct}\n{chunk}"
            }],
            stream=True
        )
    
    result_chunk = ""

    for response_chunk in stream:
        # Check if there's content to add
        if response_chunk.choices[0].delta.content is not None:
            result_chunk += response_chunk.choices[0].delta.content
        else:
            # Exit the loop if there's no more content
            break

    # Wait before processing next OpenAI request
    await asyncio.sleep(DELAY_BETWEEN_REQUESTS)

    return result_chunk

async def openai_analysis_chunked(instruct, data, model='gpt-3.5-turbo-16k'):
    print(f">>>>> Chunking data into token count of {TOKENS_PER_REQUEST}")

    # Combine the data into a single text block for analysis
    text_for_analysis = "\n\n".join(
        [f"Title: {item['title']}\nSelftext: {item['selftext']}\nComments: {' '.join(item['comments'])}" for item in data]
    )

    def num_tokens_from_string(string: str, encoding_name: str) -> int:
        """Returns the number of tokens in a text string."""
        # Get the specified encoding
        encoding = tiktoken.get_encoding(encoding_name)

        # Encode the string and count the tokens
        num_tokens = len(encoding.encode(string))

        return num_tokens

    def split_into_chunks(data, max_tokens=8000, encoding_name='cl100k_base'):
        chunks = []
        current_chunk = ""

        for post in data:
            # Prepare post text
            post_text = f"Title: {post['title']}\nSelftext: {post['selftext']}\n"

            # Check if adding this post exceeds the token limit
            if num_tokens_from_string(current_chunk + post_text, encoding_name) <= max_tokens:
                current_chunk += post_text
            else:
                # Finalize the current chunk and start a new one
                chunks.append(current_chunk)
                current_chunk = post_text

            for comment in post['comments']:
                comment_text = f"Comment: {comment}\n"

                # Check if adding this comment exceeds the token limit
                if num_tokens_from_string(current_chunk + comment_text, encoding_name) <= max_tokens:
                    current_chunk += comment_text
                else:
                    # Finalize the current chunk and start a new one
                    chunks.append(current_chunk)
                    current_chunk = comment_text

        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # Assuming you have a list of subreddit data
    chunks = split_into_chunks(data, TOKENS_PER_REQUEST, 'cl100k_base')

    # Now, 'chunks' contains the text split into smaller parts each under the token limit
    results = []

    print(f">>>>> Split into chunks: {len(chunks)}")

    # Limit the number of chunks to MAX_REQUESTS
    chunks = chunks[:MAX_REQUESTS]

    print(f">>>>> Processing max chunks: {len(chunks)}")

    for chunk in chunks:
        # Make an API call to OpenAI as a streaming request for each chunk
        result_chunk = await openai_analysis(instruct, chunk, model)

        results.append(result_chunk)

    return results

def write_to_file(filename, data):
    print(f">>>>> Writing results to {filename}")

    # If the file already exists, find a new filename
    if os.path.isfile(filename):
        i = 1
        while os.path.isfile(f"{filename}_{i}"):
            i += 1
        filename = f"{filename}_{i}"
    
    # Write the data to the file
    with open(filename, 'w') as f:
        f.write(data)
    
    print(f">>>>> Finished writing results to {filename}")

async def analyze_subreddits(subreddits):
    for subreddit in subreddits:
        # Use the functions for a specific subreddit
        subreddit_data = await get_subreddit_data(subreddit, POST_LIMIT)

        if USE_GPT4 == True:
            # Analyze the subreddit data with GPT4
            pain_point_analysis = await openai_analysis_chunked(INSTRUCT_SUMMARIZE_GPT4, subreddit_data, 'gpt-4-1106-preview')
        else:
            # Analyze the subreddit data with GPT3.5
            pain_point_analysis = await openai_analysis_chunked(INSTRUCT_SUMMARIZE, subreddit_data, 'gpt-3.5-turbo-16k')

        # Save the results to a file
        write_to_file(f"{subreddit}.md", '\n'.join(pain_point_analysis))
        
        # Print the results
        # print(pain_point_analysis)
            
        # Wait before processing next subreddit
        await asyncio.sleep(DELAY_BETWEEN_SUBREDDITS)

def main():
    print(f">>>>> Running reddit.py")

    # Create an event loop
    loop = asyncio.get_event_loop()
    
    # Use the event loop to run the async function
    loop.run_until_complete(analyze_subreddits(SUBREDDITS))

    print(f">>>>> Finished running reddit.py")

# Call the main function
if __name__ == "__main__":
    main()