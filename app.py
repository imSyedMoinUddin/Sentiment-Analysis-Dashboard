# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import praw

# --- Page Configuration ---
st.set_page_config(
    page_title="Sentiment Analysis Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- VADER Sentiment Analysis Setup ---
analyzer = SentimentIntensityAnalyzer()

# --- Core Functions ---
def get_vader_score(text):
    return analyzer.polarity_scores(text)['compound']

def classify_sentiment(score):
    if score >= 0.05: return 'Positive'
    elif score <= -0.05: return 'Negative'
    else: return 'Neutral'

# --- Data Loading and Processing Functions ---
@st.cache_data
def load_and_process_airline_data(file_path):
    df = pd.read_csv(file_path)
    df.dropna(subset=['text'], inplace=True)
    df['vader_score'] = df['text'].apply(get_vader_score)
    df['vader_sentiment'] = df['vader_score'].apply(classify_sentiment)
    return df

@st.cache_data(ttl=600)
def fetch_and_analyze_reddit_comments(subreddit_name, target_comment_count=50):
    try:
        reddit = praw.Reddit(
            client_id=st.secrets["REDDIT_CLIENT_ID"],
            client_secret=st.secrets["REDDIT_CLIENT_SECRET"],
            user_agent=f"SentimentAnalysisApp by u/{st.secrets.get('REDDIT_USERNAME', 'default_user')}"
        )
        subreddit = reddit.subreddit(subreddit_name)
        comments_list = []
        for submission in subreddit.hot(limit=30):
            if len(comments_list) >= target_comment_count: break
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                if len(comments_list) >= target_comment_count: break
                if comment.body and comment.body not in ['[deleted]', '[removed]']:
                    comments_list.append(comment.body)
        
        if not comments_list:
            st.warning("No comments found.")
            return pd.DataFrame()

        df_live = pd.DataFrame(comments_list[:target_comment_count], columns=['text'])
        df_live['vader_score'] = df_live['text'].apply(get_vader_score)
        df_live['vader_sentiment'] = df_live['vader_score'].apply(classify_sentiment)
        return df_live
    except Exception as e:
        st.error(f"An error occurred: {e}.")
        return pd.DataFrame()

# --- Main Application UI ---
# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Control Panel")
    app_mode = st.radio("Choose Analysis Mode", ("Home", "Airline Tweet Demo", "Live Reddit Analysis"))
    st.divider()
    if app_mode == "Live Reddit Analysis":
        st.subheader("Reddit Analysis Options")
        num_comments = st.slider("Number of Comments to Analyze:", min_value=25, max_value=500, value=50, step=25)
    st.divider()
    st.header("About This Project")
    st.info("An NLP dashboard for real-time sentiment analysis of social media data.")
    st.write("Created by: **Syed Moin Uddin**")
    st.write("[View on GitHub](https://github.com/your-username/your-repo-name)")

# --- Main Panel ---
st.title("📊 Social Media Sentiment Analysis")
st.markdown(f"Current Mode: **{app_mode}**")
st.divider()

# Initialize filtered_df
filtered_df = pd.DataFrame()

# --- Home Page ---
if app_mode == "Home":
    st.header("Welcome to the Sentiment Analysis Dashboard!")
    st.info("Please select an analysis mode from the sidebar to get started.")

# --- Airline Tweet Demo ---
elif app_mode == "Airline Tweet Demo":
    st.header("US Airline Tweet Sentiment Analysis")
    df_airline = load_and_process_airline_data('Tweets.csv')
    airline_choice = st.selectbox("Choose an Airline:", options=['All'] + sorted(df_airline['airline'].unique().tolist()))
    if airline_choice != 'All': 
        filtered_df = df_airline[df_airline['airline'] == airline_choice]
    else: 
        filtered_df = df_airline
    st.write(f"Displaying results for: **{airline_choice}**")

# --- Live Reddit Analysis ---
elif app_mode == "Live Reddit Analysis":
    st.header("Live Subreddit Sentiment Analysis")
    subreddit_name = st.text_input("Enter a subreddit name:", "python")
    analyze_button = st.button("Analyze Subreddit")
    if analyze_button:
        with st.spinner(f"Fetching {num_comments} comments from r/{subreddit_name}..."):
            filtered_df = fetch_and_analyze_reddit_comments(subreddit_name, num_comments)
    else:
        st.info("Enter a subreddit and adjust the slider to set the number of comments to analyze, then click the button.")

# --- Universal Display Section ---
if not filtered_df.empty:
    st.subheader("Analysis Results")
    sentiment_counts = filtered_df['vader_sentiment'].value_counts().reset_index()
    sentiment_counts.columns = ['sentiment', 'count']
    color_map = {'Positive': '#2ca02c', 'Negative': '#d62728', 'Neutral': '#7f7f7f'}
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Overall Sentiment")
        total_posts = len(filtered_df)
        positive_pct = (sentiment_counts.get('count', 0)[sentiment_counts['sentiment'] == 'Positive'].sum() / total_posts) * 100
        negative_pct = (sentiment_counts.get('count', 0)[sentiment_counts['sentiment'] == 'Negative'].sum() / total_posts) * 100
        neutral_pct = (sentiment_counts.get('count', 0)[sentiment_counts['sentiment'] == 'Neutral'].sum() / total_posts) * 100
        st.metric(label="Positive", value=f"{positive_pct:.2f}%")
        st.metric(label="Negative", value=f"{negative_pct:.2f}%")
        st.metric(label="Neutral", value=f"{neutral_pct:.2f}%")
    with col2:
        st.subheader("Sentiment Distribution")
        fig = px.pie(sentiment_counts, names='sentiment', values='count', hole=0.4, color='sentiment', color_discrete_map=color_map)
        st.plotly_chart(fig, use_container_width=True)
    
    st.divider()

    st.subheader("Explore the Raw Data")
    with st.expander("Click to view individual posts and their scores"):
        
        # --- THE FIX: Create a display-ready DataFrame with a 1-based index ---
        df_display = filtered_df[['text', 'vader_score', 'vader_sentiment']].copy()
        df_display.index = range(1, len(df_display) + 1) # Set index to start from 1
        
        def color_sentiment(sentiment):
            if sentiment == 'Positive': return 'background-color: #e6fffa'
            elif sentiment == 'Negative': return 'background-color: #ffe6e6'
            else: return 'background-color: #f0f2f6'
            
        # Apply styling to the new DataFrame with the corrected index
        styled_df = df_display.style.map(color_sentiment, subset=['vader_sentiment'])
        st.dataframe(styled_df, use_container_width=True, height=400)