# Introduction
## demo: 
    url = 'https://www.youtube.com/watch?v=x3bRer52asE'
    count = 50
    output_filename = 'Honkai.json'
    include_replies = True # if the comments include the replies
    sort_by = 'relevance' # sort by relevance or time
    debug_mode = False
## Before you do this:
    you need a YOUTUBE_API_KEY,and copy it to .env
    
## How to apply a YoutTube API Key:
    1. get a google account
    2. open the Google Cloud Console
    3. create/choose a project
    4. search YouTube Data API v3 in library(in API and service)
        enable it 
    5. Create Credentials: choose the API key, the
    console will generate a long string
    