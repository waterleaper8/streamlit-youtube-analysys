from googleapiclient.discovery import build
import json
import pandas as pd
import streamlit as st
import os

if os.path.exists('secret.json'):
    with open('secret.json') as f:
        secret_json = json.load(f)
    DEVELOPER_KEY = secret_json['apikey']
else:
    DEVELOPER_KEY = st.secrets['apikey']

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    developerKey=DEVELOPER_KEY)

def video_search(youtube, q='自動化', max_results=50):

    response = youtube.search().list(
        q=q,
        part="id,snippet",
        order='viewCount',
        type='video',
        maxResults=max_results
    ).execute()

    items_id = []
    items = response['items']
    for item in items:
        item_id = {'動画ID': '', 'channel_id': ''}
        item_id['動画ID'] = item['id']['videoId']
        item_id['channel_id'] = item['snippet']['channelId']
        items_id.append(item_id)

    df_video = pd.DataFrame(items_id)

    return df_video

def get_results(df_video, threshold_min=0, threshold_max=5000):
    try:
        channel_ids = df_video['channel_id'].unique().tolist()

        subscribers_list = youtube.channels().list(
            id=','.join(channel_ids),
            part="statistics",
            fields='items(id,statistics(subscriberCount))'
        ).execute()

        subscribers = []
        for item in subscribers_list['items']:
            subscriber = {}
            if len(item['statistics']) > 0:
                subscriber['channel_id'] = item['id']
                subscriber['登録者数'] = int(item['statistics']['subscriberCount'])
            else:
                subscriber['channel_id'] = item['id']
            subscribers.append(subscriber)

        df_subscribers = pd.DataFrame(subscribers)

        df = pd.merge(left=df_video, right=df_subscribers, on='channel_id')
        df_extracted = df[(threshold_min <= df['登録者数']) & (df['登録者数'] < threshold_max)]

        video_ids = df_extracted['動画ID'].tolist()
        videos_list = youtube.videos().list(
            id=','.join(video_ids),
            part="snippet, statistics",
            fields='items(id,snippet(title),snippet(channelTitle),statistics(viewCount))'
        ).execute()

        videos_info = []
        items = videos_list['items']
        for item in items:
            video_info = {}
            video_info['動画ID'] = item['id']
            video_info['タイトル'] = item['snippet']['title']
            video_info['チャンネル'] = item['snippet']['channelTitle']
            video_info['再生回数'] = int(item['statistics']['viewCount'])
            videos_info.append(video_info)

        df_videos_info = pd.DataFrame(videos_info)

        results = pd.merge(left=df_extracted, right=df_videos_info, on='動画ID')
        results = results.loc[:,['動画ID', 'タイトル', '再生回数', 'チャンネル', '登録者数']]
        results['登録者数'] = results['登録者数'].astype(int)
        return results
    except:
        st.warning('動画が見つかりませんでした')

st.set_page_config(page_title='YouTube分析アプリ', layout="wide", initial_sidebar_state = 'auto')
st.title('YouTube分析アプリ')

st.sidebar.write('## 検索キーワードと閾値の設定')
query = st.sidebar.text_input(label='検索キーワードの入力', placeholder='検索キーワードを入力')

st.sidebar.write('### 閾値の設定')
threshold_min, threshold_max = st.sidebar.slider('登録者数の閾値', 100, 1000000, (0, 200000))

st.write('### 選択中のパラメータ')
st.markdown(f"""
- 検索クエリ: {query}
- 登録者数の閾値: {threshold_min}-{threshold_max}
""")

df_video = video_search(youtube, q=query, max_results=50)
results = get_results(df_video, threshold_min=threshold_min, threshold_max=threshold_max)

st.write('### 分析結果', results)
st.write('### 動画再生')

video_id = st.text_input('動画IDを入力してください')
url = f'https://www.youtube.com/watch?v={video_id}'

video_field = st.empty()
video_field.write('こちらに動画が表示されます。')

if st.button('ビデオ表示'):
    if len(video_id) > 0:
        try:
            video_field.video(url)
        except :
            st.error('おっと、なにかエラーが起きているようです。')
