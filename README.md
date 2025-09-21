# Facebook Posts Search Scraper

Scrape posts from Facebook search results based on your query. Extract detailed information including post content, engagement metrics, and author details.

## Features

- Search Facebook posts by keywords or direct URL
- Extract post content, likes, comments, shares
- Filter by time range (24h, 7d, 30d, 90d)
- Support for Facebook cookie authentication
- Debug mode for troubleshooting
- Proxy support for different regions

## Input Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `searchQuery` | String | Yes* | Keywords to search for Facebook posts |
| `searchUrl` | String | Yes* | Direct Facebook search URL (alternative to searchQuery) |
| `maxPosts` | Integer | No | Maximum posts to scrape (1-5000, default: 10) |
| `postTimeRange` | String | No | Time filter: "24h", "7d", "30d", "90d" |
| `headless` | Boolean | No | Run browser in headless mode (default: true) |
| `debug` | Boolean | No | Enable debug mode (default: false) |
| `useCookies` | Boolean | No | Use Facebook cookies for authentication (default: true) |
| `facebookCookies` | String | No | Facebook cookies in JSON format |
| `proxy` | String | No | Proxy server URL |

*Either `searchQuery` or `searchUrl` must be provided.

## Output

The actor outputs an array of post objects, each containing:

```json
{
  "facebookUrl": "https://www.facebook.com/page",
  "pageId": "123456789",
  "postId": "987654321", 
  "pageName": "Page Name",
  "url": "https://www.facebook.com/page/posts/987654321",
  "time": "2025-09-22 10:30:15",
  "timestamp": 1727001015,
  "likes": 1234,
  "comments": 89,
  "shares": 156,
  "text": "Post content text...",
  "link": "https://external-link.com",
  "thumb": "https://scontent.facebook.com/image.jpg",
  "topLevelUrl": "https://www.facebook.com/page/posts/987654321",
  "facebookId": "123456789",
  "postFacebookId": "987654321"
}
```

## How to Get Facebook Cookies

For best results, provide Facebook cookies for authentication:

1. Go to Facebook.com and log in
2. Press F12 to open Developer Tools
3. Go to Application/Storage tab → Cookies → https://www.facebook.com
4. Find cookies: `c_user`, `xs`, `datr`
5. Copy their values and format as JSON:

```json
[
  {
    "name": "c_user",
    "value": "YOUR_USER_ID",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": false
  },
  {
    "name": "xs", 
    "value": "YOUR_XS_TOKEN",
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": true
  },
  {
    "name": "datr",
    "value": "YOUR_DATR_TOKEN", 
    "domain": ".facebook.com",
    "path": "/",
    "secure": true,
    "httpOnly": true
  }
]
```

## Example Usage

### Basic Search
```json
{
  "searchQuery": "artificial intelligence",
  "maxPosts": 20,
  "postTimeRange": "7d"
}
```

### With Authentication
```json
{
  "searchQuery": "machine learning",
  "maxPosts": 50,
  "useCookies": true,
  "facebookCookies": "[{\"name\":\"c_user\",\"value\":\"123456789\",\"domain\":\".facebook.com\",\"path\":\"/\",\"secure\":true,\"httpOnly\":false}]"
}
```

### Direct URL
```json
{
  "searchUrl": "https://www.facebook.com/search/posts/?q=technology",
  "maxPosts": 30
}
```

## Troubleshooting

- **No posts found**: Try enabling cookies or use different search terms
- **Login page detected**: Provide valid Facebook cookies
- **Rate limiting**: Reduce maxPosts or add delays between runs
- **Proxy issues**: Verify proxy URL format and connectivity

## Legal Notice

This actor is for educational and research purposes. Users are responsible for:
- Complying with Facebook's Terms of Service
- Respecting data privacy laws (GDPR, CCPA, etc.)
- Using scraped data ethically and legally
- Only scraping publicly available content

## Support

For issues or questions:
1. Enable debug mode to see detailed logs
2. Check that Facebook cookies are valid
3. Verify search terms return results manually
4. Review Actor run logs for error details
