# Facebook Posts Search Scraper - Complete Replica

A comprehensive replica of the `easyapi/facebook-posts-search-scraper` Actor that extracts posts from Facebook search results without paying for the original Actor.

## 🎯 Features

- ✅ **Complete Feature Parity**: Matches all functionality of the original $19.99/month Actor
- 🔍 **Search by Query or URL**: Use custom search terms or direct Facebook search URLs
- 📊 **Rich Data Extraction**: Post content, engagement metrics, author details, timestamps
- 🎛️ **Time Range Filtering**: 24h, 7d, 30d, 90d options
- 🛡️ **Anti-Detection**: Stealth browser automation with human-like behavior
- 📁 **Multiple Output Formats**: JSON with option to extend to CSV, Excel
- 🚀 **Batch Processing**: Process multiple searches automatically
- 💻 **Interactive CLI**: User-friendly command-line interface

## 📋 Extracted Data Points

Each post includes:
- `facebookUrl` - URL of the Facebook page
- `pageId` - Unique page identifier  
- `postId` - Unique post identifier
- `pageName` - Name of the Facebook page
- `url` - Direct URL to the post
- `time` - Formatted timestamp
- `timestamp` - Unix timestamp
- `likes` - Number of likes
- `comments` - Number of comments
- `shares` - Number of shares
- `text` - Post content
- `link` - Any external links
- `thumb` - Thumbnail image URL
- `topLevelUrl` - Canonical post URL
- `facebookId` - Page Facebook ID
- `postFacebookId` - Post Facebook ID

## 🛠️ Installation

### Quick Setup
```bash
# Clone or download the files
chmod +x setup.sh
./setup.sh
```

### Manual Setup
```bash
# Create virtual environment
python3 -m venv facebook_scraper_env
source facebook_scraper_env/bin/activate

# Install dependencies
pip install playwright beautifulsoup4 aiofiles

# Install browser
playwright install chromium
```

## 🚀 Usage

### 1. Interactive Mode (Recommended for beginners)
```bash
python facebook_scraper.py
```
Follow the prompts to:
- Enter search query or URL
- Set maximum posts to scrape
- Choose time range filter
- Configure headless/visible browser mode

### 2. Quick Example
```bash
python facebook_scraper.py --example
```
Runs a quick demo scraping AI-related posts.

### 3. Batch Processing
```bash
python facebook_scraper.py --batch config.json
```
Process multiple searches using a configuration file.

### 4. Programmatic Usage
```python
import asyncio
from facebook_scraper import FacebookPostsScraper

async def scrape_posts():
    scraper = FacebookPostsScraper(headless=True)
    
    posts = await scraper.search_posts(
        search_query="football",
        max_posts=50,
        post_time_range="7d"
    )
    
    filename = await scraper.save_results(posts)
    print(f"Scraped {len(posts)} posts to {filename}")

asyncio.run(scrape_posts())
```

## ⚙️ Configuration Options

### Search Parameters
- **searchQuery**: Keywords to search for
- **searchUrl**: Direct Facebook search URL (alternative to query)
- **maxPosts**: Maximum posts to scrape (1-5000)
- **postTimeRange**: Time filter (`24h`, `7d`, `30d`, `90d`)

### Browser Settings
- **headless**: Run browser in background (True/False)
- **proxy**: Proxy server for requests (optional)

### Example Batch Config
```json
{
  "jobs": [
    {
      "name": "Football Posts",
      "searchQuery": "football",
      "maxPosts": 20,
      "postTimeRange": "7d",
      "outputFile": "football_posts.json"
    }
  ]
}
```

## 🔧 Advanced Features

### Anti-Detection Measures
- Randomized user agents
- Human-like scrolling patterns
- Realistic delays between actions
- Stealth browser configuration
- Proxy support

### Error Handling
- Automatic retries for failed requests
- Graceful handling of blocked pages
- Comprehensive logging
- Resource cleanup

### Performance Optimization
- Async/await for concurrent operations
- Image and unnecessary resource blocking
- Efficient memory management
- Progress tracking

## 📊 Output Examples

### Single Post Example
```json
{
  "facebookUrl": "https://www.facebook.com/BleacherReportFootball",
  "pageId": "100044187438640",
  "postId": "1150692399746997", 
  "pageName": "Bleacher Report Football",
  "url": "https://www.facebook.com/BleacherReportFootball/posts/pfbid02KPD...",
  "time": "2024-10-01 18:11:20",
  "timestamp": 1727777480,
  "likes": 18189,
  "comments": 399,
  "shares": "2.4K",
  "text": "After 1,016 games and 38 trophies, 40-year-old Andrés Iniesta...",
  "link": "https://www.facebook.com/photo/?fbid=1150688623080708...",
  "thumb": "https://scontent-ams4-1.xx.fbcdn.net/v/t39.30808-6/461867291...",
  "topLevelUrl": "https://www.facebook.com/100044187438640/posts/1150692399746997",
  "facebookId": "100044187438640",
  "postFacebookId": "1150692399746997"
}
```

## ⚠️ Important Considerations

### Legal & Ethical
- **Terms of Service**: Facebook prohibits automated scraping
- **Rate Limiting**: Implement delays to avoid being blocked
- **Data Privacy**: Handle personal data responsibly
- **Fair Use**: Use for research, analysis, not commercial resale

### Technical Limitations
- **Public Posts Only**: Cannot access private/restricted content
- **Dynamic Structure**: Facebook frequently changes their HTML structure
- **Rate Limits**: Aggressive scraping may result in IP blocks
- **Login Required**: Some content may require authentication

### Troubleshooting
- **No Posts Found**: Try different search terms or check if login is required
- **Browser Crashes**: Increase memory limits or use headless mode
- **Blocked Requests**: Use proxies or reduce scraping speed
- **Outdated Selectors**: Update CSS selectors if Facebook changes structure

## 🆚 Comparison with Original Actor

| Feature | Original Actor | This Replica |
|---------|---------------|--------------|
| Monthly Cost | $19.99 | Free |
| Setup Time | Instant | 10 minutes |
| Customization | Limited | Full control |
| Data Format | Fixed | Customizable |
| Rate Limits | Built-in | Configure yourself |
| Updates | Automatic | Manual |
| Support | Paid | Community |

## 🔄 Maintenance

### Regular Updates
- Monitor Facebook structure changes
- Update CSS selectors as needed
- Upgrade dependencies periodically
- Test functionality regularly

### Performance Monitoring
```bash
# Check logs
tail -f scraper.log

# Monitor resource usage
htop

# Test connectivity
python -c "import asyncio; from facebook_scraper import FacebookPostsScraper; scraper = FacebookPostsScraper(); print('✅ Import successful')"
```

## 🤝 Contributing

Feel free to:
- Report issues and bugs
- Suggest improvements
- Submit pull requests
- Share usage examples

## 📝 License

This project is for educational purposes. Please ensure compliance with:
- Facebook's Terms of Service
- Local laws regarding web scraping
- Data protection regulations (GDPR, CCPA, etc.)

## 🆘 Support

### Common Issues
1. **"No posts found"**: Check if content requires login
2. **"Browser crashes"**: Try headless mode or increase memory
3. **"Connection refused"**: Use proxy or VPN
4. **"Outdated selectors"**: Update CSS selectors in code

### Getting Help
- Check the logs for error details
- Try running in non-headless mode to see what's happening
- Reduce the number of posts for testing
- Use different search terms

---

**Disclaimer**: This tool is for educational and research purposes. Users are responsible for ensuring compliance with applicable terms of service and laws.