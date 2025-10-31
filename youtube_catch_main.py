import os
import json
import argparse
import logging
import time
import random
import re
import socket
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
import ssl
# help to find the error
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# set the API key
from config import YOUTUBE_API_KEY

# maxmum to try
MAX_RETRIES = 3

# the file to be saved
SAVE_DIR = os.path.join("data", "youtube")


def get_video_id_from_url(url):
    if re.match(r'^[A-Za-z0-9_-]{11}$', url):
        return url

    # 处理各种YouTube URL格式
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0].split("&")[0]

    elif "youtube.com/shorts/" in url:
        return url.split("youtube.com/shorts/")[-1].split("?")[0].split("&")[0]

    elif "youtube.com/watch" in url:
        match = re.search(r'v=([A-Za-z0-9_-]{11})', url)
        if match:
            return match.group(1)

    # the format can not be identified (无法识别的URL格式)
    logger.error(f"can not get the Video ID: {url}")
    return None

"""check if the video ID is valid"""
def validate_video_id(video_id):

    if not video_id:
        return False

    if not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        return False

    try:
        response = requests.get(
            f"https://www.youtube.com/oembed?url=http://www.youtube.com/watch?v={video_id}&format=json")
        return response.status_code == 200
    except:
        print('the error may be the website')
        return True


def save_comments_to_file(comments, file_path, is_final=False):
    try:
        # make sure the makedirs is existing
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        if is_final:
            logger.info(f"✅ store {len(comments)} comments to {file_path}")
        else:
            logger.debug(f"already have stored {len(comments)} comments to {file_path}")
    except Exception as e:
        logger.error(f"fail to store json to path: {str(e)}")

# try again when facing error
def execute_with_retry(func, *args, **kwargs):
    retries = 0
    while retries < MAX_RETRIES:
        try:
            return func(*args, **kwargs)
        except (ssl.SSLError, socket.error, ConnectionError) as e:
            retries += 1
            wait_time = 2 ** retries
            logger.warning(f"websites error: {str(e)}, the {retries} time try, wait for {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:

            raise e

    raise Exception(f"still fail after {MAX_RETRIES} try")


def get_comments(video_url, count=100, output_filename=None, include_replies=True,
                 sort_by="relevance", debug_mode=False):
    if debug_mode:
        logger.setLevel(logging.DEBUG)

    # 评论列表
    comment_list = []

    try:
        # if we do not set the output file name
        video_id = get_video_id_from_url(video_url)

        if not video_id:
            logger.error("check the url format")
            return comment_list

        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = os.path.join(SAVE_DIR, f"youtube_{video_id}_{timestamp}.json")
        else:
            if not output_filename.startswith(SAVE_DIR):
                output_filename = os.path.join(SAVE_DIR, os.path.basename(output_filename))

        # create a empty json
        save_comments_to_file([], output_filename)

        # 验证视频ID
        if not validate_video_id(video_id):
            logger.error(f"the video url or ID may be false: {video_id}")
            return comment_list

        logger.info(f"start to get YouTube comments: {video_id}")
        logger.info(f"plan to get  {count} comments" + " if include_replies else ")

        # create YouTube API
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY, cache_discovery=False)

        # comment request parameters
        comment_kwargs = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': min(100, count),
            'order': sort_by,  # 'relevance' or 'time'
            'textFormat': 'plainText'
        }

        next_page_token = None
        comment_count = 0
        total_comments = 0
        last_save_count = 0

        while comment_count < count:

            if next_page_token:
                comment_kwargs['pageToken'] = next_page_token

            # try to get comment
            try:

                response = execute_with_retry(
                    lambda: youtube.commentThreads().list(**comment_kwargs).execute()
                )

                # check if it has comments
                if 'items' not in response or len(response['items']) == 0:
                    logger.info("the video do not have any comments")
                    break

            except HttpError as e:
                if "videoNotFound" in str(e) or "404" in str(e):
                    logger.error(f"the url is empty: {video_id}")
                elif "commentsDisabled" in str(e):
                    logger.error("the video have banned the commments")
                else:
                    logger.error(f"YouTube API错误: {e}")
                break

            # deal with comments
            for item in response['items']:
                # avoid too many comments
                if comment_count >= count:
                    break

                # random delay
                if random.random() < 0.2:
                    micro_delay = random.uniform(0.1, 0.5)
                    time.sleep(micro_delay)
                try:
                    comment_info = item['snippet']['topLevelComment']['snippet']

                    comment_data = {
                        "text": comment_info['textDisplay'],
                        "like_count": comment_info['likeCount'],
                        "platform": "youtube"
                    }
                    # get reply
                    if include_replies and item['snippet']['totalReplyCount'] > 0:
                        try:

                            replies_response = execute_with_retry(
                                lambda: youtube.comments().list(
                                    part='snippet',
                                    parentId=item['id'],
                                    maxResults=100
                                ).execute()
                            )

                            for reply_item in replies_response.get('items', []):
                                reply_info = reply_item['snippet']

                                reply_data = {
                                    "text": reply_info['textDisplay'],
                                    "like_count": reply_info['likeCount'],
                                    "platform": "youtube"
                                }

                                comment_list.append(reply_data)
                                total_comments += 1

                            if len(replies_response.get('items', [])) > 0:
                                logger.info(
                                    f"the comment number #{comment_count + 1} get {len(replies_response.get('items', []))} replies")

                        except Exception as e:
                            logger.warning(f"error when deal with comments: {str(e)}")

                    comment_list.append(comment_data)
                    comment_count += 1
                    total_comments += 1

                    # save again when comment_count = 10
                    if comment_count % 10 == 0:
                        logger.info(f"get {comment_count} main comments (include {total_comments} replies)...")
                        # save
                        save_comments_to_file(comment_list, output_filename)
                        last_save_count = comment_count

                        # random sleep
                        rest_time = random.uniform(1.0, 2.0)
                        logger.debug(f"rest {rest_time:.2f} seconds...")
                        time.sleep(rest_time)

                except Exception as e:
                    logger.warning(f"error when deal with comments: {str(e)}")
                    continue

            # check if it has the next page
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        # save the last comments
        if comment_count > last_save_count:
            save_comments_to_file(comment_list, output_filename, is_final=True)

        logger.info(f"✅ get comment successfully - {comment_count} main comments (the sum is  {total_comments} (including replies))")
        return comment_list

    except KeyboardInterrupt:
        # if user stop the process
        logger.info("saving the stored comments...")
        if comment_list:
            save_comments_to_file(comment_list, output_filename, is_final=True)
        logger.info(f"already store {len(comment_list)} comments to {output_filename}")
        return comment_list

    except Exception as e:
        # try to get stored comments when error happened
        logger.error(f"fail when get comment: {str(e)}")
        if comment_list:
            logger.info("try to save comments...")
            save_comments_to_file(comment_list, output_filename, is_final=True)
        return comment_list


def main():
    url = 'https://www.youtube.com/watch?v=x3bRer52asE'
    count = 50
    output_filename = 'Honkai.json'
    include_replies = True #
    sort_by = 'relevance' # relevance or time
    debug_mode = False
    try:
        get_comments(
            url,
            count,
            output_filename,
            include_replies,
            sort_by,
            debug_mode
        )
    except KeyboardInterrupt:
        logger.info("programme have exited")
    except Exception as e:
        logger.error(f"error happened: {str(e)}")

if __name__ == "__main__":
    main()


