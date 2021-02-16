import pandas as pd
import pymysql
import isodate
import re
import nltk

from googleapiclient.discovery import build
from textblob import TextBlob
from textblob.en.sentiments import NaiveBayesAnalyzer
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


def setup_mysql_connection():
    # database connection
    return pymysql.connect(host="mysql", user="root", passwd="helloworld")


def initialise_database():
    cursor.execute("""CREATE DATABASE IF NOT EXISTS youtube_analysis""")
    cursor.execute("""USE youtube_analysis""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS Video(
                ID INT(20) PRIMARY KEY AUTO_INCREMENT,
                VIDEO_ID VARCHAR(50) NOT NULL,
                TITLE TEXT,
                LINK VARCHAR(100),
                DURATION INT,
                PA FLOAT DEFAULT NULL,
                NBA FLOAT DEFAULT NULL,
                UNIQUE KEY `VIDEO_ID_UNIQUE` (`VIDEO_ID`))""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS Subtitle(
                ID INT(20) PRIMARY KEY AUTO_INCREMENT,
                VIDEO_ID VARCHAR(50) NOT NULL,
                SUBTITLE TEXT,
                CONSTRAINT FK_VideoId FOREIGN KEY (VIDEO_ID) REFERENCES Video(VIDEO_ID))""")


def close_mysql_connection():
    connection.commit()
    connection.close()


def setup_youtube_api_client():
    return build('youtube', 'v3', developerKey='<Youtube API key>')


def get_search_results():
    request = youtube.search().list(
        part='snippet',
        maxResults=50,
        q=f'spongebob squarepants cartoon english subtitles'
    )
    response = request.execute()

    videos = []
    for item in response['items']:
        # The results are not only videos so need to distinguish between them
        if item['id']['kind'] == 'youtube#video':
            videos.append(item['id']['videoId'])
    return videos


def get_videos_details_dataframe():
    df = pd.DataFrame()
    for video_id in youtube_videos:
        request = youtube.videos().list(
            part="snippet,contentDetails",
            id=video_id
        )
        response = request.execute()
        for item in response['items']:
            content_details = item['contentDetails']
            df = df.append({
                'video_id': video_id,
                'link': f'https://www.youtube.com/watch?v={video_id}',
                'title': item['snippet']['title'],
                'duration': isodate.parse_duration(content_details['duration']).total_seconds(),
            }, ignore_index=True)
    return df


def insert_into_video(videos):
    cursor.executemany("""INSERT INTO Video 
    (DURATION, LINK, TITLE, VIDEO_ID) 
    VALUES (%s, %s, %s, %s)""", videos)


def download_subtitles(videos):
    subs_text = []
    for video in videos:
        try:
            subtitles = YouTubeTranscriptApi.get_transcript(video)
            text_list = []
            for i in subtitles:
                text_list.append(i['text'])
            text = ' '.join(text_list)
            text = text.replace("\n", " ")
            text = re.sub(r"\((.*?)\)", "", text)
            text = re.sub(r"\[(.*?)\]", "", text)
            subs_text.append([video, text])
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            print('Video with id ', video, ' does not have subtitles')
    cursor.executemany("""INSERT INTO Subtitle (VIDEO_ID, SUBTITLE) VALUES (%s, %s)""", subs_text)


def fetch_all_subs():
    cursor.execute("""SELECT * from Subtitle;""")
    return cursor.fetchall()


def calculate_and_persist_subs_sentiment():
    for row in rows:
        print(row[1], row[2])
        pattern_analyser = TextBlob(row[2])
        naive_bayes_analyser = TextBlob(row[2], analyzer=NaiveBayesAnalyzer())
        cursor.execute(
            f'UPDATE Video SET '
            f'PA = {pattern_analyser.sentiment.polarity}, '
            f'NBA = {naive_bayes_analyser.sentiment.p_pos} WHERE VIDEO_ID = \'{row[1]}\''
        )


if __name__ == '__main__':
    nltk.download('movie_reviews')
    nltk.download('punkt')
    cartoon_name = 'spongebob squarepants'
    print('Starting YouTube subs sentiment Analysis')
    connection = setup_mysql_connection()
    cursor = connection.cursor()
    initialise_database()
    print('MySQL youtube database has been initialised')
    youtube = setup_youtube_api_client()
    youtube_videos = get_search_results()
    print('Retrieved the following video ids: ', youtube_videos)
    youtube_videos_details = get_videos_details_dataframe()
    # Filter criteria 1: Cartoon name should be present either on title or description
    print('Filter criteria 1: Cartoon name should be present either on title or description')
    youtube_videos_details = youtube_videos_details[
        youtube_videos_details['title'].str.contains(cartoon_name, case=False)
    ]

    # Filter criteria 2: Exclude movie, compilation, episodes results since the duration defers from the median duration
    # In our case we decided to exclude the videos that last two times longer thank the median duration.
    print('Filter criteria 2: Exclude movie, compilation, episodes results since the duration defers from '
          'the median duration')
    youtube_videos_details = youtube_videos_details[
        (youtube_videos_details['duration'] <= youtube_videos_details['duration'].median() * 2) &
        ~(youtube_videos_details['title'].str.contains('compilation', case=False) |
          youtube_videos_details['title'].str.contains('episodes', case=False) |
          youtube_videos_details['title'].str.contains('movie', case=False))
    ]
    # Persist filtered results to database
    insert_into_video(youtube_videos_details.values.tolist())
    print('Videos has been persisted')
    # Persist video subs to database
    download_subtitles(youtube_videos_details['video_id'])
    print('Video subs have been persisted')
    rows = fetch_all_subs()
    calculate_and_persist_subs_sentiment()
    print('Subs sentiment has been persisted')
    close_mysql_connection()
