import requests
import json
import os
from datetime import datetime, timedelta

ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
COMPANY_ID = "70998576"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "X-Restli-Protocol-Version": "2.0.0",
    "LinkedIn-Version": "202401"
}

def get_follower_stats():
    url = f"https://api.linkedin.com/v2/organizationalEntityFollowerStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{COMPANY_ID}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        elements = data.get("elements", [])
        if elements:
            return elements[0].get("followerCountsByAssociationType", [])
    return []

def get_page_stats():
    end = int(datetime.now().timestamp() * 1000)
    start = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    url = (
        f"https://api.linkedin.com/v2/organizationPageStatistics"
        f"?q=organization&organization=urn:li:organization:{COMPANY_ID}"
        f"&timeIntervals.timeGranularityType=DAY"
        f"&timeIntervals.timeRange.start={start}"
        f"&timeIntervals.timeRange.end={end}"
    )
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("elements", [])
    return []

def get_share_stats():
    end = int(datetime.now().timestamp() * 1000)
    start = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
    url = (
        f"https://api.linkedin.com/v2/organizationalEntityShareStatistics"
        f"?q=organizationalEntity&organizationalEntity=urn:li:organization:{COMPANY_ID}"
        f"&timeIntervals.timeGranularityType=DAY"
        f"&timeIntervals.timeRange.start={start}"
        f"&timeIntervals.timeRange.end={end}"
    )
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("elements", [])
    return []

def get_posts():
    url = f"https://api.linkedin.com/v2/shares?q=owners&owners=urn:li:organization:{COMPANY_ID}&sortBy=LAST_MODIFIED&count=20"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("elements", [])
    return []

def get_post_stats(share_urns):
    if not share_urns:
        return []
    urn_list = "&".join([f"shares[{i}]={urn}" for i, urn in enumerate(share_urns)])
    url = f"https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{COMPANY_ID}&{urn_list}"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json().get("elements", [])
    return []

# --- Collect all data ---
print("Fetching LinkedIn data...")

follower_data = get_follower_stats()
page_stats = get_page_stats()
share_stats = get_share_stats()
posts = get_posts()

share_urns = [p.get("activity") or p.get("id", "") for p in posts[:10]]
post_stats = get_post_stats(share_urns)

# --- Aggregate totals ---
total_followers = 0
for f in follower_data:
    total_followers += f.get("followerCounts", {}).get("organicFollowerCount", 0)
    total_followers += f.get("followerCounts", {}).get("paidFollowerCount", 0)

total_views = sum(
    e.get("totalPageStatistics", {}).get("views", {}).get("allPageViews", {}).get("pageViews", 0)
    for e in page_stats
)
total_unique = sum(
    e.get("totalPageStatistics", {}).get("views", {}).get("allPageViews", {}).get("uniquePageViews", 0)
    for e in page_stats
)

total_impressions = sum(
    e.get("totalShareStatistics", {}).get("impressionCount", 0)
    for e in share_stats
)
total_clicks = sum(
    e.get("totalShareStatistics", {}).get("clickCount", 0)
    for e in share_stats
)
total_likes = sum(
    e.get("totalShareStatistics", {}).get("likeCount", 0)
    for e in share_stats
)
total_comments = sum(
    e.get("totalShareStatistics", {}).get("commentCount", 0)
    for e in share_stats
)
total_shares = sum(
    e.get("totalShareStatistics", {}).get("shareCount", 0)
    for e in share_stats
)

# engagement rate
engagement_rate = 0
if total_impressions > 0:
    engagement_rate = round((total_likes + total_comments + total_shares + total_clicks) / total_impressions * 100, 2)

# --- Daily trend data ---
daily_views = []
for e in page_stats:
    ts = e.get("timeRange", {}).get("start", 0)
    views = e.get("totalPageStatistics", {}).get("views", {}).get("allPageViews", {}).get("pageViews", 0)
    date_str = datetime.fromtimestamp(ts / 1000).strftime("%m/%d")
    daily_views.append({"date": date_str, "views": views})

daily_impressions = []
for e in share_stats:
    ts = e.get("timeRange", {}).get("start", 0)
    impressions = e.get("totalShareStatistics", {}).get("impressionCount", 0)
    date_str = datetime.fromtimestamp(ts / 1000).strftime("%m/%d")
    daily_impressions.append({"date": date_str, "impressions": impressions})

# --- Post list ---
post_list = []
for i, p in enumerate(posts):
    text = ""
    specific = p.get("specificContent", {})
    share_content = specific.get("com.linkedin.ugc.ShareContent", {}) or specific.get("com.linkedin.share.ShareContent", {})
    commentary = share_content.get("shareCommentary", {})
    if commentary:
        text = commentary.get("text", "")[:100]

    stat = post_stats[i] if i < len(post_stats) else {}
    ts_stats = stat.get("totalShareStatistics", {})

    created = p.get("created", {}).get("time", 0)
    date_str = datetime.fromtimestamp(created / 1000).strftime("%Y-%m-%d") if created else ""

    post_list.append({
        "id": p.get("id", ""),
        "text": text,
        "date": date_str,
        "impressions": ts_stats.get("impressionCount", 0),
        "clicks": ts_stats.get("clickCount", 0),
        "likes": ts_stats.get("likeCount", 0),
        "comments": ts_stats.get("commentCount", 0),
        "shares": ts_stats.get("shareCount", 0),
    })

# --- Save output ---
output = {
    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "overview": {
        "followers": total_followers,
        "page_views_30d": total_views,
        "unique_visitors_30d": total_unique,
        "impressions_30d": total_impressions,
        "clicks_30d": total_clicks,
        "likes_30d": total_likes,
        "comments_30d": total_comments,
        "shares_30d": total_shares,
        "engagement_rate": engagement_rate,
    },
    "daily_views": daily_views,
    "daily_impressions": daily_impressions,
    "posts": post_list
}

os.makedirs("docs/data", exist_ok=True)
with open("docs/data/linkedin.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Done! Followers: {total_followers}, Views: {total_views}, Posts: {len(post_list)}")
