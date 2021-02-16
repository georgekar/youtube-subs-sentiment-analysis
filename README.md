# Youtube subs sentiment analysis

This simple example on using textblob library for sentiment analysis. Subtitles of Spongebob Squarepants have been 
selected for this application.

## Application tech components

- Youtube api client, using an API key
- youtube_transcript_api, for downloading subtitles
- textblob
- MySQL docker container
- PhpMyAdmin docker container

## Application flow

Initially, database has been initialised and right after 50 videos are being fetched from Youtube. After, applying some 
filtering on those videos we persist them under table VIDEO. Next, subtitles (if exist) are downloaded and persisted
in table SUBTITLE. At last but not least, the subtitle text is retrieved from the database and passed through 
PatternAnalyser and NaiveBayesAnalyser. The result of those analysers is pesisted in table VIDEO next to respective 
video.

## Run application

- Create a Youtube API key https://developers.google.com/youtube/v3/getting-started
- Replace the created key in app/app.py setup_youtube_api_client() method
- docker-compose up
- Wait for the app to be up and running and access phpmyadmin in http://localhost:8080
- Username: root, Password: helloworld
- Check results in youtube_analysis database
- docker-compose down to stop the app


