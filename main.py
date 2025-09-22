import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import base64
from playwright.async_api import async_playwright, BrowserContext, Page
from apify import Actor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedFacebookPostsScraper:
    def __init__(self, input_data: Dict[str, Any]):
        self.input_data = input_data
        self.max_posts = input_data.get('maxPosts', 10)
        self.search_query = input_data.get('searchQuery', '')
        self.post_time_range = input_data.get('postTimeRange', '24h')
        self.use_cookies = input_data.get('useCookies', False)
        self.facebook_cookies = input_data.get('facebookCookies', '')
        self.debug = input_data.get('debug', False)
        self.proxy_config = input_data.get('proxyConfiguration', {})
        
        self.browser_context = None
        self.scraped_posts = []
        
    async def setup_browser(self):
        """Initialize browser with proxy and cookie support"""
        playwright = await async_playwright().start()
        
        # BULLETPROOF FIX: Multiple ways to detect Apify platform and force headless
        # Check multiple environment variables that indicate Apify platform
        apify_indicators = [
            os.getenv('APIFY_IS_AT_HOME'),
            os.getenv('APIFY_ACTOR_ID'),
            os.getenv('APIFY_ACTOR_RUN_ID'),
            os.getenv('APIFY_TOKEN'),
            os.getenv('APIFY_DEFAULT_DATASET_ID')
        ]
        
        # If ANY Apify environment variable exists, we're on Apify platform
        is_apify_platform = any(var for var in apify_indicators if var)
        
        # Also check if we're in a container (another indicator)
        is_container = os.path.exists('/.dockerenv') or os.getenv('container') == 'docker'
        
        # Force headless if on Apify platform OR in container OR debug is False
        # This ensures headless mode in almost all server environments
        headless_mode = True if (is_apify_platform or is_container) else (not self.debug)
        
        # SAFETY: If we're still not sure, check if DISPLAY variable exists
        # If no DISPLAY, we MUST use headless mode
        if not os.getenv('DISPLAY'):
            headless_mode = True
            
        logger.info(f"Platform detection - Apify: {is_apify_platform}, Container: {is_container}, Headless: {headless_mode}")
        
        # Browser launch options with headless FORCED
        launch_options = {
            'headless': headless_mode,  # This will be True on Apify/containers
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
                '--no-zygote',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows'
            ]
        }
        
        # Add proxy configuration if provided
        if self.proxy_config.get('useApifyProxy'):
            proxy_groups = self.proxy_config.get('apifyProxyGroups', ['RESIDENTIAL'])
            proxy_country = self.proxy_config.get('apifyProxyCountry', 'US')
            launch_options['proxy'] = {
                'server': f'http://groups-{"+".join(proxy_groups)},country-{proxy_country}:apify_proxy_password@proxy.apify.com:8000'
            }
        elif self.proxy_config.get('proxyUrls'):
            proxy_url = self.proxy_config['proxyUrls'][0]
            launch_options['proxy'] = {'server': proxy_url}
        
        browser = await playwright.chromium.launch(**launch_options)
        logger.info(f"Browser launched successfully (headless: {headless_mode})")
        
        # Create context with additional settings
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        self.browser_context = await browser.new_context(**context_options)
        return self.browser_context

    def parse_cookies(self) -> List[Dict[str, Any]]:
        """Parse Facebook cookies from input"""
        if not self.facebook_cookies:
            return []
        
        try:
            cookies = json.loads(self.facebook_cookies)
            # Convert to Playwright cookie format
            playwright_cookies = []
            
            for cookie in cookies:
                playwright_cookie = {
                    'name': cookie.get('name'),
                    'value': cookie.get('value'),
                    'domain': cookie.get('domain', '.facebook.com'),
                    'path': cookie.get('path', '/'),
                    'secure': cookie.get('secure', True),
                    'httpOnly': cookie.get('httpOnly', False),
                    'sameSite': self._convert_same_site(cookie.get('sameSite', 'no_restriction'))
                }
                
                # Add expiration if present
                if 'expirationDate' in cookie:
                    playwright_cookie['expires'] = int(cookie['expirationDate'])
                
                playwright_cookies.append(playwright_cookie)
            
            logger.info(f"Parsed {len(playwright_cookies)} cookies")
            return playwright_cookies
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse cookies: {e}")
            return []

    def _convert_same_site(self, same_site: str) -> str:
        """Convert sameSite values to Playwright format"""
        mapping = {
            'no_restriction': 'None',
            'lax': 'Lax',
            'strict': 'Strict'
        }
        return mapping.get(same_site.lower(), 'None')

    async def set_cookies(self, page: Page):
        """Set Facebook cookies with validation"""
        if not self.use_cookies:
            logger.info("Cookie usage disabled")
            return False
        
        cookies = self.parse_cookies()
        if not cookies:
            logger.warning("No cookies to set")
            return False
        
        try:
            # Navigate to Facebook first to set cookies
            logger.info("Navigating to Facebook homepage to set cookies...")
            await page.goto('https://www.facebook.com', wait_until='domcontentloaded', timeout=45000)
            await asyncio.sleep(3)
            
            # Set cookies individually with validation
            successful_cookies = 0
            for cookie in cookies:
                try:
                    await self.browser_context.add_cookies([cookie])
                    logger.info(f"Set cookie: {cookie['name']}")
                    successful_cookies += 1
                except Exception as e:
                    logger.warning(f"Failed to set cookie {cookie['name']}: {e}")
            
            logger.info(f"Successfully set {successful_cookies}/{len(cookies)} cookies")
            
            # IMPROVED: Use domcontentloaded instead of networkidle for faster loading
            try:
                await page.reload(wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(2)
                logger.info("Page reloaded successfully")
            except Exception as e:
                logger.warning(f"Page reload timeout (this is often normal): {e}")
                # Continue anyway - cookies might still work
            
            # Check authentication more reliably
            try:
                # Wait a bit for page to settle
                await asyncio.sleep(3)
                
                # Check for login indicators
                login_selectors = [
                    'input[name="email"]',
                    'input[name="pass"]',
                    '[data-testid="royal_login_form"]',
                    '#loginform'
                ]
                
                is_login_page = False
                for selector in login_selectors:
                    count = await page.locator(selector).count()
                    if count > 0:
                        is_login_page = True
                        logger.info(f"Found login element: {selector}")
                        break
                
                if not is_login_page:
                    logger.info("No login elements detected - authentication likely successful")
                    return True
                else:
                    logger.warning("Login page detected - authentication may have failed")
                    return False
                    
            except Exception as e:
                logger.warning(f"Authentication check failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Cookie setup failed: {e}")
            return False

    def build_search_url(self) -> str:
        """Build Facebook search URL with filters"""
        base_url = "https://www.facebook.com/search/posts"
        encoded_query = quote_plus(self.search_query.strip())
        
        # Build time-based filters
        filters = {}
        
        if self.post_time_range:
            now = datetime.now()
            if self.post_time_range == '24h':
                start_date = now - timedelta(days=1)
            elif self.post_time_range == '7d':
                start_date = now - timedelta(days=7)
            elif self.post_time_range == '30d':
                start_date = now - timedelta(days=30)
            else:
                start_date = now - timedelta(days=1)  # Default to 24h
            
            # Add creation time filter
            filters['rp_creation_time:0'] = {
                "name": "creation_time",
                "args": {
                    "start_year": str(start_date.year),
                    "start_month": f"{start_date.year}-{start_date.month:02d}",
                    "end_year": str(now.year),
                    "end_month": f"{now.year}-{now.month:02d}",
                    "start_day": f"{start_date.year}-{start_date.month}-{start_date.day}",
                    "end_day": f"{now.year}-{now.month}-{now.day}"
                }
            }
        
        # Add recent posts filter
        filters['recent_posts:0'] = {"name": "recent_posts", "args": ""}
        
        # Add chronological sort
        filters['rp_chrono_sort:0'] = {"name": "chronosort", "args": ""}
        
        if filters:
            # Encode filters as base64 JSON
            filters_json = json.dumps(filters, separators=(',', ':'))
            filters_encoded = base64.b64encode(filters_json.encode()).decode()
            return f"{base_url}?q={encoded_query}&filters={filters_encoded}"
        else:
            return f"{base_url}?q={encoded_query}&filters=recent"

    async def extract_posts(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts from the page with improved error handling"""
        posts = []
        
        try:
            logger.info("Waiting for page content to load...")
            
            # Try multiple approaches to wait for content
            wait_strategies = [
                # Strategy 1: Wait for posts
                ('[role="article"], [data-pagelet="FeedUnit"]', 15000),
                # Strategy 2: Wait for any content area
                ('div[data-pagelet], main, #mount_0_0_V5', 10000),
                # Strategy 3: Just wait for basic page structure
                ('body', 5000)
            ]
            
            content_loaded = False
            for selector, timeout in wait_strategies:
                try:
                    await page.wait_for_selector(selector, timeout=timeout)
                    logger.info(f"Content loaded using selector: {selector}")
                    content_loaded = True
                    break
                except:
                    logger.info(f"Timeout waiting for: {selector}")
                    continue
            
            if not content_loaded:
                logger.warning("No content selectors worked - checking page manually")
            
            # Wait a bit more for dynamic content
            await asyncio.sleep(5)
            
            # Check if we're on login page
            login_count = await page.locator('input[name="email"]').count()
            if login_count > 0:
                logger.error("Still on login page - cookies may have expired or failed")
                return posts
            
            # Try multiple post selectors
            post_selectors = [
                '[role="article"]',
                '[data-pagelet="FeedUnit"]',
                '.userContentWrapper',
                '._5jmm',
                '[data-testid="post_message"]',
                'div[data-pagelet]'
            ]
            
            post_elements = []
            for selector in post_selectors:
                try:
                    elements = await page.locator(selector).all()
                    if elements and len(elements) > 0:
                        post_elements = elements
                        logger.info(f"Found {len(elements)} elements using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not post_elements:
                logger.warning("No post elements found with any selector")
                
                # Fallback: Try to get any text content
                logger.info("Attempting fallback text extraction...")
                try:
                    page_text = await page.inner_text('body')
                    if len(page_text) > 100:
                        logger.info(f"Page has content ({len(page_text)} characters)")
                        # Create a basic post entry with page content sample
                        fallback_post = {
                            'text': page_text[:500] + '...' if len(page_text) > 500 else page_text,
                            'author': 'Unknown',
                            'timestamp': datetime.now().isoformat(),
                            'likes': 0,
                            'comments': 0,
                            'shares': 0,
                            'post_url': page.url,
                            'extracted_at': datetime.now().isoformat(),
                            'extraction_method': 'fallback'
                        }
                        posts.append(fallback_post)
                        logger.info("Added fallback content extraction")
                except Exception as e:
                    logger.error(f"Fallback extraction failed: {e}")
                
                return posts
            
            # Process found post elements
            for i, post_element in enumerate(post_elements[:self.max_posts]):
                try:
                    post_data = await self.extract_single_post(post_element, page)
                    if post_data:
                        posts.append(post_data)
                        logger.info(f"Extracted post {i+1}: {post_data.get('text', '')[:100]}...")
                    else:
                        logger.debug(f"Post {i+1} had no extractable content")
                        
                except Exception as e:
                    logger.warning(f"Failed to extract post {i+1}: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(posts)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error extracting posts: {e}")
            return posts

    async def extract_single_post(self, post_element, page: Page) -> Optional[Dict[str, Any]]:
        """Extract data from a single post"""
        try:
            post_data = {
                'text': '',
                'author': '',
                'timestamp': '',
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'post_url': '',
                'images': [],
                'extracted_at': datetime.now().isoformat()
            }
            
            # Extract post text
            text_selectors = [
                '[data-testid="post_message"]',
                '.userContent',
                '._5pbx',
                '.text_exposed_root'
            ]
            
            for selector in text_selectors:
                text_element = post_element.locator(selector).first
                if await text_element.count() > 0:
                    post_data['text'] = await text_element.inner_text()
                    break
            
            # Extract author name
            author_selectors = [
                'h3 a',
                '.actor-link',
                '[data-testid="post_author_name"]',
                'strong'
            ]
            
            for selector in author_selectors:
                author_element = post_element.locator(selector).first
                if await author_element.count() > 0:
                    post_data['author'] = await author_element.inner_text()
                    break
            
            # Extract timestamp
            time_selectors = [
                'abbr',
                '[data-testid="story-subtitle"] a',
                '.timestamp',
                'time'
            ]
            
            for selector in time_selectors:
                time_element = post_element.locator(selector).first
                if await time_element.count() > 0:
                    timestamp_text = await time_element.get_attribute('title') or await time_element.inner_text()
                    post_data['timestamp'] = timestamp_text
                    break
            
            # Extract engagement metrics
            try:
                # Likes
                like_selectors = ['[aria-label*="like"]', '[data-testid="like_count"]']
                for selector in like_selectors:
                    like_element = post_element.locator(selector).first
                    if await like_element.count() > 0:
                        like_text = await like_element.inner_text()
                        post_data['likes'] = self.parse_count(like_text)
                        break
                
                # Comments
                comment_selectors = ['[aria-label*="comment"]', '[data-testid="comment_count"]']
                for selector in comment_selectors:
                    comment_element = post_element.locator(selector).first
                    if await comment_element.count() > 0:
                        comment_text = await comment_element.inner_text()
                        post_data['comments'] = self.parse_count(comment_text)
                        break
                        
            except Exception as e:
                logger.debug(f"Failed to extract engagement metrics: {e}")
            
            # Extract post URL
            try:
                permalink_selectors = ['a[href*="/posts/"]', 'a[href*="/permalink/"]']
                for selector in permalink_selectors:
                    link_element = post_element.locator(selector).first
                    if await link_element.count() > 0:
                        href = await link_element.get_attribute('href')
                        if href:
                            post_data['post_url'] = f"https://www.facebook.com{href}" if href.startswith('/') else href
                            break
            except Exception as e:
                logger.debug(f"Failed to extract post URL: {e}")
            
            # Only return posts with meaningful content
            if post_data['text'] or post_data['author']:
                return post_data
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error extracting single post: {e}")
            return None

    def parse_count(self, count_text: str) -> int:
        """Parse count strings like '1.2K', '500', etc."""
        if not count_text:
            return 0
        
        try:
            # Remove non-numeric characters except K, M, B
            clean_text = ''.join(c for c in count_text if c.isdigit() or c in 'KMB.')
            
            if 'K' in clean_text:
                return int(float(clean_text.replace('K', '')) * 1000)
            elif 'M' in clean_text:
                return int(float(clean_text.replace('M', '')) * 1000000)
            elif 'B' in clean_text:
                return int(float(clean_text.replace('B', '')) * 1000000000)
            else:
                return int(clean_text) if clean_text else 0
        except:
            return 0

    async def scrape_posts(self) -> List[Dict[str, Any]]:
        """Main scraping method"""
        try:
            # Setup browser
            await self.setup_browser()
            page = await self.browser_context.new_page()
            
            # Set cookies if enabled
            if self.use_cookies:
                await self.set_cookies(page)
            
            # Build search URL
            search_url = self.build_search_url()
            logger.info(f"Navigating to: {search_url}")
            
            # Navigate with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await page.goto(search_url, wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(5)
                    break
                except Exception as e:
                    logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(5)
            
            # Check if we need to handle login
            if await page.locator('input[name="email"]').count() > 0:
                logger.warning("Login page detected - limited access")
            
            # Extract posts
            posts = await self.extract_posts(page)
            
            return posts
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
        finally:
            if self.browser_context:
                await self.browser_context.close()

async def main():
    """Main entry point for Apify Actor"""
    async with Actor:
        # Get input
        input_data = await Actor.get_input() or {}
        logger.info(f"Input received: {input_data}")
        
        # Validate input - ensure we have a search query
        search_query = input_data.get('searchQuery', '').strip()
        search_url = input_data.get('searchUrl', '').strip()
        
        if not search_query and not search_url:
            error_msg = "Either 'searchQuery' or 'searchUrl' must be provided"
            logger.error(error_msg)
            await Actor.set_status_message(error_msg)
            return
        
        # Initialize scraper
        scraper = EnhancedFacebookPostsScraper(input_data)
        
        try:
            # Scrape posts
            posts = await scraper.scrape_posts()
            
            # Save results
            for post in posts:
                await Actor.push_data(post)
            
            logger.info(f"Successfully scraped {len(posts)} posts")
            
            # Set final status message
            await Actor.set_status_message(f"Completed: scraped {len(posts)} posts")
            
        except Exception as e:
            error_msg = f"Scraping error: {str(e)}"
            logger.error(error_msg)
            # FIXED: Use proper error handling
            await Actor.set_status_message(error_msg)
            # Don't use Actor.abort() or Actor.exit() - just let the Actor finish
            # The Actor will exit naturally with the error status message

if __name__ == "__main__":
    asyncio.run(main())
