#!/usr/bin/env python3
"""
Facebook Posts Search Scraper - Complete Working Version
Replicates easyapi/facebook-posts-search-scraper functionality with cookie authentication
"""

import asyncio
import json
import re
import random
import time
import os
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin, urlparse, parse_qs
from typing import List, Dict, Optional, Any
import logging

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Missing required package: {e}")
    print("Please install required packages:")
    print("pip install playwright beautifulsoup4")
    print("playwright install chromium")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FacebookCookieManager:
    """Manages Facebook cookies for authentication"""
    
    def __init__(self, cookies_file: str = "facebook_cookies.json"):
        self.cookies_file = cookies_file
        self.cookies = []
    
    def load_cookies_from_file(self) -> bool:
        """Load cookies from JSON file"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    self.cookies = json.load(f)
                logger.info(f"Loaded {len(self.cookies)} cookies from {self.cookies_file}")
                return True
            else:
                logger.warning(f"Cookie file {self.cookies_file} not found")
                return False
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return False
    
    def save_cookies_to_file(self, cookies: List[Dict]) -> bool:
        """Save cookies to JSON file"""
        try:
            with open(self.cookies_file, 'w') as f:
                json.dump(cookies, f, indent=2)
            logger.info(f"Saved {len(cookies)} cookies to {self.cookies_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
            return False

class FacebookPostsScraper:
    """Complete Facebook Posts Search Scraper with cookie authentication"""
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None, debug: bool = False, 
                 cookies_file: str = "facebook_cookies.json"):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = headless
        self.proxy = proxy
        self.debug = debug
        self.scraped_post_ids = set()
        self.cookie_manager = FacebookCookieManager(cookies_file)
        
        # Enhanced user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        ]
    
    async def setup_browser(self, use_cookies: bool = True) -> None:
        """Initialize browser with enhanced stealth configuration and cookies"""
        playwright = await async_playwright().start()
        
        # Enhanced browser arguments
        launch_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-dev-shm-usage',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-ipc-flooding-protection',
            '--disable-features=TranslateUI',
            '--disable-translate',
            '--disable-background-networking',
            '--disable-sync',
            '--metrics-recording-only',
            '--disable-default-apps',
            '--mute-audio',
            '--no-zygote',
            '--disable-gpu-sandbox',
        ]
        
        if self.headless:
            launch_args.append('--disable-images')
        
        if self.proxy:
            launch_args.append(f'--proxy-server={self.proxy}')
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
            slow_mo=100 if not self.headless else 0
        )
        
        # Enhanced context options
        context_options = {
            'user_agent': random.choice(self.user_agents),
            'viewport': {'width': 1366, 'height': 768},
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': [],
            'color_scheme': 'light',
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Load cookies if available
        if use_cookies and self.cookie_manager.load_cookies_from_file():
            try:
                await self.context.add_cookies(self.cookie_manager.cookies)
                logger.info("Facebook cookies loaded successfully")
            except Exception as e:
                logger.warning(f"Error loading cookies into context: {e}")
        
        if self.headless:
            await self.context.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,mp4,webm}", 
                                    lambda route: route.abort())
        
        self.page = await self.context.new_page()
        
        # Enhanced stealth scripts
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            window.chrome = {
                runtime: {},
                csi: function(){},
                loadTimes: function(){},
                app: {}
            };
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [{
                    0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        logger.info("Browser setup completed")
    
    async def verify_authentication(self) -> bool:
        """Verify if we're successfully authenticated with Facebook"""
        try:
            await self.page.goto('https://www.facebook.com/', wait_until='domcontentloaded', timeout=15000)
            await self.page.wait_for_timeout(3000)
            
            page_content = await self.page.content()
            
            # Check for signs of successful authentication
            auth_indicators = ['data-testid="royal_header"', 'composer', 'newsfeed', 'profile']
            login_indicators = ['login', 'Log in', 'Sign up', 'password', 'email']
            
            is_authenticated = any(indicator in page_content for indicator in auth_indicators)
            needs_login = any(indicator in page_content.lower() for indicator in login_indicators)
            
            if is_authenticated and not needs_login:
                logger.info("Successfully authenticated with Facebook")
                return True
            else:
                logger.warning("Not authenticated - login page detected")
                if self.debug:
                    await self.page.screenshot(path='debug_login_page.png')
                return False
                
        except Exception as e:
            logger.error(f"Error verifying authentication: {e}")
            return False
    
    async def search_posts(self, search_query: str = None, search_url: str = None, 
                          max_posts: int = 100, post_time_range: str = None, 
                          use_cookies: bool = True) -> List[Dict[str, Any]]:
        """Main method to search and scrape Facebook posts"""
        try:
            await self.setup_browser(use_cookies=use_cookies)
            
            # Verify authentication if using cookies
            if use_cookies:
                is_authenticated = await self.verify_authentication()
                if not is_authenticated:
                    logger.warning("Authentication failed. Proceeding without cookies...")
            
            if search_url:
                url = search_url
            elif search_query:
                url = self._build_search_url(search_query, post_time_range)
            else:
                raise ValueError("Either search_query or search_url must be provided")
            
            logger.info(f"Starting scrape for: {search_query or search_url}")
            logger.info(f"Target URL: {url}")
            
            await self._navigate_to_page(url)
            
            if self.debug and not self.headless:
                await self.page.screenshot(path='debug_initial_page.png')
                logger.info("Debug screenshot saved: debug_initial_page.png")
            
            await self._handle_overlays()
            await self._wait_for_content()
            
            # Check if we're still on a login page after navigation
            page_content = await self.page.content()
            if any(indicator in page_content.lower() for indicator in ['log in', 'sign up', 'email or phone']):
                logger.warning("Still on login page - may need valid cookies")
                if self.debug:
                    await self.page.screenshot(path='debug_still_login.png')
            
            posts = await self._scrape_posts(max_posts)
            
            logger.info(f"Successfully scraped {len(posts)} posts")
            return posts
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            if self.debug:
                try:
                    await self.page.screenshot(path='debug_error.png')
                    html = await self.page.content()
                    with open('debug_page.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    logger.info("Debug files saved: debug_error.png, debug_page.html")
                except:
                    pass
            raise
        finally:
            await self.cleanup()
    
    def setup_cookies_interactive(self) -> bool:
        """Interactive cookie setup for users"""
        print("\n" + "="*60)
        print("FACEBOOK COOKIES SETUP")
        print("="*60)
        print("To access Facebook posts, you need to provide your Facebook cookies.")
        print("This allows the scraper to authenticate as you.\n")
        
        print("How to get your Facebook cookies:")
        print("1. Open Facebook.com in your browser and log in")
        print("2. Press F12 to open Developer Tools")
        print("3. Go to Application/Storage tab -> Cookies -> https://www.facebook.com")
        print("4. Find these important cookies:")
        print("   - c_user (your user ID)")
        print("   - xs (session token)")
        print("   - datr (browser token)")
        print("5. Copy their values\n")
        
        choice = input("How would you like to input cookies?\n1. Manual input\n2. Create template file\n3. Skip (may not work)\nChoice (1-3): ").strip()
        
        if choice == "1":
            return self._manual_cookie_input()
        elif choice == "2":
            return self._create_cookie_template()
        else:
            print("WARNING: Skipping cookies - scraper may not work properly")
            return False
    
    def _manual_cookie_input(self) -> bool:
        """Manual cookie input interface"""
        print("\nEnter your Facebook cookies:")
        
        cookies = []
        required_cookies = ['c_user', 'xs', 'datr']
        
        for cookie_name in required_cookies:
            value = input(f"Enter {cookie_name} value: ").strip()
            if value:
                cookies.append({
                    'name': cookie_name,
                    'value': value,
                    'domain': '.facebook.com',
                    'path': '/',
                    'secure': True,
                    'httpOnly': cookie_name in ['xs', 'datr']
                })
        
        if cookies:
            if self.cookie_manager.save_cookies_to_file(cookies):
                print("SUCCESS: Cookies saved successfully!")
                return True
        
        print("ERROR: No cookies saved")
        return False
    
    def _create_cookie_template(self) -> bool:
        """Create a template file for users"""
        template = {
            "instructions": [
                "1. Go to facebook.com in your browser and log in",
                "2. Press F12 to open Developer Tools",
                "3. Go to Application/Storage tab -> Cookies -> https://www.facebook.com",
                "4. Find cookies named: c_user, xs, datr",
                "5. Copy their values and replace the YOUR_*_HERE placeholders below",
                "6. Save this file as facebook_cookies.json"
            ],
            "cookies": [
                {
                    "name": "c_user",
                    "value": "YOUR_USER_ID_HERE",
                    "domain": ".facebook.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": False
                },
                {
                    "name": "xs",
                    "value": "YOUR_XS_TOKEN_HERE",
                    "domain": ".facebook.com", 
                    "path": "/",
                    "secure": True,
                    "httpOnly": True
                },
                {
                    "name": "datr",
                    "value": "YOUR_DATR_TOKEN_HERE",
                    "domain": ".facebook.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True
                }
            ]
        }
        
        try:
            with open('facebook_cookies_template.json', 'w') as f:
                json.dump(template, f, indent=2)
            
            print("SUCCESS: Template created: facebook_cookies_template.json")
            print("Edit this file with your actual cookie values, then rename it to facebook_cookies.json")
            return False
            
        except Exception as e:
            print(f"ERROR: Error creating template: {e}")
            return False

    def _build_search_url(self, query: str, time_range: str = None) -> str:
        """Build Facebook search URL with filters"""
        base_url = f"https://www.facebook.com/search/posts/?q={quote(query)}"
        
        if time_range:
            if time_range in ['24h', '7d', '30d', '90d']:
                return f"{base_url}&filters=recent"
        
        return base_url
    
    async def _navigate_to_page(self, url: str) -> None:
        """Navigate to page with error handling"""
        max_retries = 3
        urls_to_try = [
            url,
            url.replace('www.facebook.com', 'm.facebook.com'),
        ]
        
        for attempt in range(max_retries):
            for i, test_url in enumerate(urls_to_try):
                try:
                    logger.info(f"Navigating to page (attempt {attempt + 1}, URL variant {i + 1})")
                    if self.debug:
                        logger.info(f"URL: {test_url}")
                    
                    await self.page.goto(test_url, wait_until='domcontentloaded', timeout=30000)
                    await self.page.wait_for_timeout(random.uniform(3000, 5000))
                    
                    current_url = self.page.url
                    if self.debug:
                        logger.info(f"Current URL after navigation: {current_url}")
                    
                    page_text = await self.page.text_content('body')
                    if page_text and len(page_text) > 100:
                        return
                    
                except Exception as e:
                    logger.warning(f"Navigation attempt {attempt + 1}, variant {i + 1} failed: {e}")
                    if attempt == max_retries - 1 and i == len(urls_to_try) - 1:
                        raise
                    await asyncio.sleep(random.uniform(2, 5))
    
    async def _wait_for_content(self) -> None:
        """Wait for page content to load properly"""
        try:
            selectors_to_wait = [
                '[role="main"]',
                '[data-testid="fbfeed_story"]', 
                '[role="article"]',
                '.userContentWrapper',
                '[data-pagelet*="FeedUnit"]',
                'div[data-ft]'
            ]
            
            for selector in selectors_to_wait:
                try:
                    await self.page.wait_for_selector(selector, timeout=5000)
                    if self.debug:
                        logger.info(f"Found content with selector: {selector}")
                    break
                except:
                    continue
            else:
                logger.warning("No expected content selectors found, proceeding anyway")
            
            await self.page.wait_for_timeout(3000)
            
        except Exception as e:
            logger.warning(f"Error waiting for content: {e}")
    
    async def _handle_overlays(self) -> None:
        """Handle blocking overlays and popups"""
        try:
            overlay_selectors = [
                '[data-testid="cookie-policy-manage-dialog"]',
                '[role="dialog"]',
                '[aria-label*="Close"]',
                'button[aria-label*="Not now"]',
                'button[aria-label*="Skip"]',
                '[data-testid="close-button"]'
            ]
            
            for selector in overlay_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for element in elements:
                        if await element.is_visible():
                            await element.click()
                            await self.page.wait_for_timeout(1000)
                            if self.debug:
                                logger.info(f"Closed overlay: {selector}")
                            break
                except Exception:
                    continue
            
            await self.page.keyboard.press('Escape')
            await self.page.wait_for_timeout(1000)
                    
        except Exception as e:
            logger.warning(f"Error handling overlays: {e}")
    
    async def _scrape_posts(self, max_posts: int) -> List[Dict[str, Any]]:
        """Main scraping loop"""
        posts = []
        no_new_posts_count = 0
        max_no_new_posts = 5
        
        while len(posts) < max_posts and no_new_posts_count < max_no_new_posts:
            await self._scroll_page()
            
            if self.debug:
                page_text = await self.page.text_content('body')
                logger.info(f"Page text length: {len(page_text) if page_text else 0}")
            
            new_posts = await self._extract_posts_from_page()
            
            unique_new_posts = []
            for post in new_posts:
                if post.get('postId') and post['postId'] not in self.scraped_post_ids:
                    unique_new_posts.append(post)
                    self.scraped_post_ids.add(post['postId'])
            
            if unique_new_posts:
                posts.extend(unique_new_posts)
                no_new_posts_count = 0
                logger.info(f"Found {len(unique_new_posts)} new posts. Total: {len(posts)}")
            else:
                no_new_posts_count += 1
                logger.info(f"No new posts found (attempt {no_new_posts_count})")
                
                if self.debug and no_new_posts_count == 2:
                    await self.page.screenshot(path=f'debug_no_posts_{no_new_posts_count}.png')
            
            await asyncio.sleep(random.uniform(3, 6))
            
            if len(posts) >= max_posts:
                break
        
        return posts[:max_posts]
    
    async def _extract_posts_from_page(self) -> List[Dict[str, Any]]:
        """Extract post data from current page state"""
        posts = []
        
        try:
            await self.page.wait_for_timeout(2000)
            
            post_selectors = [
                '[data-pagelet*="FeedUnit"]',
                '[data-testid="fbfeed_story"]',
                '[role="article"]',
                'div[data-ft]',
                '.userContentWrapper',
                'div[class*="story"]',
                'div[class*="post"]',
                'div:has(> div:has(a[href*="posts"]))',
                'div:has(> div:has(a[href*="story.php"]))'
            ]
            
            post_elements = []
            selector_used = None
            
            for selector in post_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if elements and len(elements) > 0:
                        post_elements = elements
                        selector_used = selector
                        if self.debug:
                            logger.info(f"Found {len(elements)} elements using selector: {selector}")
                        break
                except Exception as e:
                    if self.debug:
                        logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not post_elements:
                logger.warning("No post elements found with any selector")
                return []
            
            for i, element in enumerate(post_elements):
                try:
                    post_data = await self._extract_single_post(element)
                    if post_data and post_data.get('postId'):
                        posts.append(post_data)
                        if self.debug:
                            logger.info(f"Successfully extracted post {i+1}: {post_data.get('postId')}")
                except Exception as e:
                    logger.warning(f"Error extracting post {i+1}: {e}")
                    continue
            
            if self.debug:
                logger.info(f"Total posts extracted: {len(posts)} from {len(post_elements)} elements using selector: {selector_used}")
            
        except Exception as e:
            logger.error(f"Error extracting posts from page: {e}")
        
        return posts

    async def _extract_single_post(self, element) -> Optional[Dict[str, Any]]:
        """Extract data from a single post element"""
        try:
            post_url = await self._get_post_url(element)
            if not post_url:
                try:
                    all_links = await element.locator('a[href*="facebook.com"]').all()
                    for link in all_links:
                        href = await link.get_attribute('href')
                        if href and any(indicator in href for indicator in ['posts', 'story', 'permalink']):
                            post_url = self._normalize_facebook_url(href)
                            break
                except:
                    pass
            
            if not post_url:
                return None
            
            post_id = self._extract_id_from_url(post_url, 'post')
            if not post_id:
                post_id = str(hash(post_url))[-10:]
            
            page_link = await self._find_page_link(element)
            page_url = await self._get_link_href(page_link) if page_link else None
            page_id = self._extract_id_from_url(page_url, 'page') if page_url else None
            page_name = await self._get_text_content(page_link) if page_link else "Unknown"
            
            if page_name == "Unknown":
                try:
                    author_selectors = [
                        'strong[dir="auto"]',
                        '[data-testid="post_author_name"]',
                        'h3 a',
                        '[role="button"] strong'
                    ]
                    
                    for selector in author_selectors:
                        name_elem = element.locator(selector).first
                        if await name_elem.count() > 0:
                            name_text = await name_elem.text_content()
                            if name_text and len(name_text.strip()) > 0:
                                page_name = name_text.strip()
                                break
                except:
                    pass
            
            post_text = await self._extract_post_text(element)
            timestamp_data = await self._extract_timestamp(element)
            engagement = await self._extract_engagement_metrics(element)
            media_data = await self._extract_media(element)
            
            post_data = {
                'facebookUrl': page_url,
                'pageId': page_id,
                'postId': post_id,
                'pageName': page_name,
                'url': post_url,
                'time': timestamp_data.get('formatted'),
                'timestamp': timestamp_data.get('unix'),
                'likes': engagement.get('likes', 0),
                'comments': engagement.get('comments', 0), 
                'shares': engagement.get('shares', 0),
                'text': post_text,
                'link': media_data.get('link'),
                'thumb': media_data.get('thumb'),
                'topLevelUrl': post_url,
                'facebookId': page_id,
                'postFacebookId': post_id
            }
            
            return post_data
            
        except Exception as e:
            logger.warning(f"Error extracting single post: {e}")
            return None

    async def _get_post_url(self, element) -> Optional[str]:
        """Extract post URL from element"""
        try:
            selectors = [
                'a[href*="/posts/"]',
                'a[href*="/permalink/"]', 
                'a[href*="/story.php"]',
                'a[aria-label*="permalink"]',
                'a[role="link"][href*="facebook.com"]',
                'a[href*="story_fbid"]',
                'a[href*="pfbid"]'
            ]
            
            for selector in selectors:
                links = await element.locator(selector).all()
                for link in links:
                    href = await link.get_attribute('href')
                    if href and any(indicator in href for indicator in ['posts', 'permalink', 'story.php', 'story_fbid', 'pfbid']):
                        return self._normalize_facebook_url(href)
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Error getting post URL: {e}")
        
        return None

    async def _find_page_link(self, element):
        """Find the page/author link in the post"""
        try:
            selectors = [
                '[data-testid="story-subtitle"] a',
                'h3 a',
                '[role="link"][href*="facebook.com/"]:not([href*="/posts/"]):not([href*="/story.php"])',
                'a[href*="facebook.com/"][aria-label]:not([href*="/posts/"])',
                'strong[dir="auto"] a'
            ]
            
            for selector in selectors:
                links = await element.locator(selector).all()
                for link in links:
                    href = await link.get_attribute('href')
                    if href and 'facebook.com' in href and not any(x in href for x in ['posts', 'story.php', 'permalink']):
                        return link
                        
        except Exception:
            pass
        
        return None

    async def _get_link_href(self, element) -> Optional[str]:
        """Get normalized href from link element"""
        try:
            if element:
                href = await element.get_attribute('href')
                return self._normalize_facebook_url(href) if href else None
        except Exception:
            pass
        return None

    async def _get_text_content(self, element) -> Optional[str]:
        """Get text content from element"""
        try:
            if element:
                text = await element.text_content()
                return text.strip() if text else None
        except Exception:
            pass
        return None

    async def _extract_post_text(self, element) -> Optional[str]:
        """Extract the main post text content"""
        try:
            text_selectors = [
                '[data-testid="post_message"]',
                '[data-testid="story-subtitle"] + div',
                '.userContent',
                '[dir="auto"]:not(strong):not(h1):not(h2):not(h3)'
            ]
            
            for selector in text_selectors:
                text_elements = await element.locator(selector).all()
                for text_elem in text_elements:
                    text = await text_elem.text_content()
                    if text and len(text.strip()) > 20:
                        return text.strip()
            
            try:
                all_text = await element.text_content()
                if all_text and len(all_text.strip()) > 50:
                    lines = all_text.split('\n')
                    content_lines = [line.strip() for line in lines if len(line.strip()) > 20]
                    if content_lines:
                        return content_lines[0]
            except:
                pass
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Error extracting post text: {e}")
        
        return None

    async def _extract_timestamp(self, element) -> Dict[str, Any]:
        """Extract timestamp information"""
        try:
            time_selectors = [
                'time',
                '[data-testid="story-subtitle"] a',
                'a[role="link"][aria-label*="ago"]',
                'abbr[data-utime]'
            ]
            
            for selector in time_selectors:
                time_elements = await element.locator(selector).all()
                for time_elem in time_elements:
                    datetime_attr = await time_elem.get_attribute('datetime')
                    if datetime_attr:
                        try:
                            dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                            return {
                                'formatted': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'unix': int(dt.timestamp())
                            }
                        except Exception:
                            pass
                    
                    utime = await time_elem.get_attribute('data-utime')
                    if utime:
                        try:
                            dt = datetime.fromtimestamp(int(utime))
                            return {
                                'formatted': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'unix': int(utime)
                            }
                        except Exception:
                            pass
                    
                    title = await time_elem.get_attribute('title')
                    aria_label = await time_elem.get_attribute('aria-label')
                    text_content = await time_elem.text_content()
                    
                    for attr in [title, aria_label, text_content]:
                        if attr:
                            parsed_time = self._parse_facebook_time(attr)
                            if parsed_time:
                                return parsed_time
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Error extracting timestamp: {e}")
        
        return {'formatted': None, 'unix': None}

    async def _extract_engagement_metrics(self, element) -> Dict[str, int]:
        """Extract likes, comments, shares counts"""
        engagement = {'likes': 0, 'comments': 0, 'shares': 0}
        
        try:
            element_text = await element.text_content()
            
            if element_text:
                patterns = {
                    'likes': [
                        r'(\d+(?:,\d+)*)\s*(?:like|reaction)',
                        r'(\d+(?:\.\d+)?[KM]?)\s*(?:like|reaction)'
                    ],
                    'comments': [
                        r'(\d+(?:,\d+)*)\s*(?:comment)',
                        r'(\d+(?:\.\d+)?[KM]?)\s*(?:comment)'
                    ],
                    'shares': [
                        r'(\d+(?:,\d+)*)\s*(?:share)',
                        r'(\d+(?:\.\d+)?[KM]?)\s*(?:share)'
                    ]
                }
                
                for metric, pattern_list in patterns.items():
                    for pattern in pattern_list:
                        matches = re.finditer(pattern, element_text.lower())
                        for match in matches:
                            count_str = match.group(1)
                            engagement[metric] = max(engagement[metric], self._parse_count(count_str))
            
            engagement_selectors = [
                '[aria-label*="like"]',
                '[aria-label*="comment"]', 
                '[aria-label*="share"]'
            ]
            
            for selector in engagement_selectors:
                elements = await element.locator(selector).all()
                for elem in elements:
                    aria_label = await elem.get_attribute('aria-label')
                    text_content = await elem.text_content()
                    
                    for text in [aria_label, text_content]:
                        if text:
                            text_lower = text.lower()
                            if any(word in text_lower for word in ['like', 'love', 'reaction']):
                                count = self._extract_count_from_text(text)
                                engagement['likes'] = max(engagement['likes'], count)
                            elif 'comment' in text_lower:
                                count = self._extract_count_from_text(text)
                                engagement['comments'] = max(engagement['comments'], count)
                            elif 'share' in text_lower:
                                count = self._extract_count_from_text(text)
                                engagement['shares'] = max(engagement['shares'], count)
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Error extracting engagement metrics: {e}")
        
        return engagement

    async def _extract_media(self, element) -> Dict[str, Optional[str]]:
        """Extract media URLs (images, links)"""
        media = {'thumb': None, 'link': None}
        
        try:
            img_selectors = [
                'img[src*="scontent"]',
                'img[src*="fbcdn"]',
                'img:not([src*="data:"])'
            ]
            
            for selector in img_selectors:
                img_elements = await element.locator(selector).all()
                for img in img_elements:
                    src = await img.get_attribute('src')
                    if src and not src.startswith('data:') and len(src) > 20:
                        media['thumb'] = src
                        break
                if media['thumb']:
                    break
            
            link_selectors = [
                'a[href*="l.facebook.com"]',
                'a[href*="lm.facebook.com"]'
            ]
            
            for selector in link_selectors:
                link_elements = await element.locator(selector).all()
                for link in link_elements:
                    href = await link.get_attribute('href')
                    if href:
                        decoded_link = self._decode_facebook_link(href)
                        if decoded_link:
                            media['link'] = decoded_link
                            break
                if media['link']:
                    break
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Error extracting media: {e}")
        
        return media

    async def _scroll_page(self) -> None:
        """Scroll page to load more content"""
        try:
            prev_height = await self.page.evaluate("document.body.scrollHeight")
            
            await self.page.evaluate("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            
            await self.page.wait_for_timeout(random.uniform(2000, 4000))
            
            new_height = await self.page.evaluate("document.body.scrollHeight")
            
            if new_height == prev_height:
                await self.page.keyboard.press('End')
                await self.page.wait_for_timeout(2000)
            
        except Exception as e:
            logger.warning(f"Error scrolling page: {e}")

    def _extract_id_from_url(self, url: str, id_type: str) -> Optional[str]:
        """Extract post or page ID from Facebook URL"""
        if not url:
            return None
        
        try:
            if id_type == 'post':
                patterns = [
                    r'/posts/(\d+)',
                    r'/permalink/(\d+)',
                    r'story_fbid=(\d+)',
                    r'pfbid([A-Za-z0-9]+)',
                    r'/story\.php.*?story_fbid=(\d+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, url)
                    if match:
                        return match.group(1) if match.group(1).isdigit() else match.group(0)
                
                return str(abs(hash(url)))[-10:]
            
            elif id_type == 'page':
                patterns = [
                    r'facebook\.com/(\d+)',
                    r'facebook\.com/pages/[^/]+/(\d+)',
                    r'id=(\d+)',
                    r'facebook\.com/([^/?]+)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, url)
                    if match:
                        page_id = match.group(1)
                        if page_id.isdigit():
                            return page_id
                        elif not any(x in page_id for x in ['posts', 'story', 'permalink']):
                            return page_id
                        
        except Exception as e:
            if self.debug:
                logger.debug(f"Error extracting {id_type} ID from URL {url}: {e}")
        
        return None

    def _normalize_facebook_url(self, url: str) -> str:
        """Normalize Facebook URL"""
        if not url:
            return url
        
        if url.startswith('/'):
            url = f"https://www.facebook.com{url}"
        
        clean_url = re.sub(r'[?&]__tn__=[^&]*', '', url)
        clean_url = re.sub(r'[?&]__cft__\[[^\]]*\]=[^&]*', '', clean_url)
        
        return clean_url

    def _parse_facebook_time(self, time_str: str) -> Optional[Dict[str, Any]]:
        """Parse Facebook time string to datetime"""
        try:
            now = datetime.now()
            time_str_lower = time_str.lower()
            
            if any(phrase in time_str_lower for phrase in ['just now', 'few seconds', 'moments ago']):
                dt = now
            elif 'minute' in time_str_lower:
                match = re.search(r'(\d+)\s*minute', time_str_lower)
                minutes = int(match.group(1)) if match else 1
                dt = now - timedelta(minutes=minutes)
            elif 'hour' in time_str_lower:
                match = re.search(r'(\d+)\s*hour', time_str_lower)
                hours = int(match.group(1)) if match else 1
                dt = now - timedelta(hours=hours)
            elif 'day' in time_str_lower or 'yesterday' in time_str_lower:
                if 'yesterday' in time_str_lower:
                    dt = now - timedelta(days=1)
                else:
                    match = re.search(r'(\d+)\s*day', time_str_lower)
                    days = int(match.group(1)) if match else 1
                    dt = now - timedelta(days=days)
            elif 'week' in time_str_lower:
                match = re.search(r'(\d+)\s*week', time_str_lower)
                weeks = int(match.group(1)) if match else 1
                dt = now - timedelta(weeks=weeks)
            else:
                date_patterns = [
                    '%B %d, %Y at %I:%M %p',
                    '%B %d at %I:%M %p',
                    '%m/%d/%Y',
                    '%Y-%m-%d'
                ]
                
                for pattern in date_patterns:
                    try:
                        dt = datetime.strptime(time_str, pattern)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            
            return {
                'formatted': dt.strftime('%Y-%m-%d %H:%M:%S'),
                'unix': int(dt.timestamp())
            }
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Error parsing time '{time_str}': {e}")
            return None

    def _parse_count(self, count_str: str) -> int:
        """Parse count string (e.g., '1.2K' -> 1200)"""
        if not count_str:
            return 0
        
        clean_str = re.sub(r'[,\s]', '', str(count_str)).upper()
        
        try:
            if 'K' in clean_str:
                number = float(clean_str.replace('K', ''))
                return int(number * 1000)
            elif 'M' in clean_str:
                number = float(clean_str.replace('M', ''))
                return int(number * 1000000)
            elif 'B' in clean_str:
                number = float(clean_str.replace('B', ''))
                return int(number * 1000000000)
            else:
                number_match = re.search(r'(\d+(?:\.\d+)?)', clean_str)
                if number_match:
                    return int(float(number_match.group(1)))
                    
        except (ValueError, TypeError):
            pass
        
        return 0

    def _extract_count_from_text(self, text: str) -> int:
        """Extract numeric count from text"""
        if not text:
            return 0
        
        patterns = [
            r'(\d+(?:\.\d+)?[KMB])',
            r'(\d+(?:,\d+)*)',
            r'(\d+(?:\.\d+)?)\s*(?:thousand|million|billion)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return self._parse_count(matches[0])
        
        return 0

    def _decode_facebook_link(self, encoded_url: str) -> Optional[str]:
        """Decode Facebook wrapped links"""
        try:
            if any(domain in encoded_url for domain in ['l.facebook.com', 'lm.facebook.com']):
                parsed = urlparse(encoded_url)
                params = parse_qs(parsed.query)
                
                for param_name in ['u', 'url', 'next']:
                    if param_name in params:
                        return params[param_name][0]
                        
        except Exception:
            pass
        
        return None

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        try:
            if self.context:
                try:
                    current_cookies = await self.context.cookies()
                    if current_cookies:
                        self.cookie_manager.save_cookies_to_file(current_cookies)
                except Exception as e:
                    logger.warning(f"Error saving current cookies: {e}")
            
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            
            logger.info("Browser cleanup completed")
                
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    async def save_results(self, posts: List[Dict[str, Any]], filename: str = None) -> str:
        """Save results to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"facebook_posts_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Results saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise


class FacebookScraperCLI:
    """Command line interface with cookie support"""
    
    def __init__(self):
        self.scraper = None
    
    async def run_interactive(self):
        """Interactive mode with cookie setup"""
        print("=" * 70)
        print("FACEBOOK POSTS SEARCH SCRAPER - COOKIE AUTHENTICATION VERSION")
        print("=" * 70)
        
        cookie_file = "facebook_cookies.json"
        has_cookies = os.path.exists(cookie_file)
        
        if not has_cookies:
            print("No Facebook cookies found.")
            scraper_temp = FacebookPostsScraper()
            if not scraper_temp.setup_cookies_interactive():
                print("\nWARNING: Proceeding without cookies (may not work properly)")
                has_cookies = False
            else:
                has_cookies = True
        else:
            print("SUCCESS: Found existing Facebook cookies")
            update_cookies = input("Update cookies? (y/n): ").strip().lower() == 'y'
            if update_cookies:
                scraper_temp = FacebookPostsScraper()
                scraper_temp.setup_cookies_interactive()
        
        print("\n" + "="*50)
        search_query = input("Enter search query (or press Enter to use URL): ").strip()
        
        if not search_query:
            search_url = input("Enter Facebook search URL: ").strip()
            if not search_url:
                print("Error: Either search query or URL is required")
                return
        else:
            search_url = None
        
        try:
            max_posts = int(input("Maximum posts to scrape (default 10): ").strip() or "10")
        except ValueError:
            max_posts = 10
        
        time_range = input("Time range filter (24h/7d/30d/90d, or press Enter for none): ").strip()
        if time_range not in ['24h', '7d', '30d', '90d']:
            time_range = None
        
        headless = input("Run in headless mode? (y/n, default y): ").strip().lower() != 'n'
        debug = input("Enable debug mode? (y/n, default n): ").strip().lower() == 'y'
        
        print(f"\nStarting cookie-authenticated scrape...")
        print(f"Query: {search_query or search_url}")
        print(f"Max posts: {max_posts}")
        print(f"Time range: {time_range or 'None'}")
        print(f"Headless: {headless}")
        print(f"Debug: {debug}")
        print(f"Using cookies: {has_cookies}")
        print("-" * 50)
        
        try:
            self.scraper = FacebookPostsScraper(headless=headless, debug=debug)
            
            posts = await self.scraper.search_posts(
                search_query=search_query,
                search_url=search_url,
                max_posts=max_posts,
                post_time_range=time_range,
                use_cookies=has_cookies
            )
            
            if posts:
                filename = await self.scraper.save_results(posts)
                
                print(f"\nSUCCESS!")
                print(f"Scraped {len(posts)} posts")
                print(f"Results saved to: {filename}")
                
                self._show_sample_results(posts[:3])
                
            else:
                print("\nERROR: No posts found")
                if not has_cookies:
                    print("\nTIP: Try setting up Facebook cookies:")
                    print("   Run the scraper again and choose option 1 or 2 for cookie setup")
                elif debug:
                    print("\nDEBUG: Check debug files for more information:")
                    print("  - debug_error.png")
                    print("  - debug_page.html")
                    print("  - debug_login_page.png")
                
        except Exception as e:
            print(f"\nERROR: {e}")
            logger.error(f"Scraping failed: {e}")
            if debug:
                print("\nDEBUG: Check debug files for error details")
    
    def _show_sample_results(self, posts: List[Dict[str, Any]]):
        """Show sample results"""
        print("\nSample Results:")
        print("=" * 60)
        
        for i, post in enumerate(posts, 1):
            print(f"\nPost {i}:")
            print(f"  Page: {post.get('pageName', 'Unknown')}")
            print(f"  Time: {post.get('time', 'Unknown')}")
            print(f"  Likes: {post.get('likes', 0)}")
            print(f"  Comments: {post.get('comments', 0)}")
            print(f"  Shares: {post.get('shares', 0)}")
            
            text = post.get('text', '')
            if text:
                preview = text[:150] + "..." if len(text) > 150 else text
                print(f"  Text: {preview}")
            
            if post.get('thumb'):
                print(f"  Image: Yes")
            
            if post.get('link'):
                print(f"  External Link: Yes")
                
            print(f"  URL: {post.get('url', 'N/A')}")


async def main():
    """Main execution function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--setup-cookies':
        scraper = FacebookPostsScraper()
        scraper.setup_cookies_interactive()
        
    elif len(sys.argv) > 1 and sys.argv[1] == '--debug':
        scraper = FacebookPostsScraper(headless=False, debug=True)
        
        print("Running debug mode with cookies...")
        posts = await scraper.search_posts(
            search_query="artificial intelligence",
            max_posts=3,
            use_cookies=True
        )
        
        filename = await scraper.save_results(posts)
        print(f"Debug completed: {len(posts)} posts saved to {filename}")
        
    elif len(sys.argv) > 1 and sys.argv[1] == '--example':
        scraper = FacebookPostsScraper(headless=True, debug=False)
        
        print("Running example with cookies...")
        posts = await scraper.search_posts(
            search_query="technology news",
            max_posts=5,
            use_cookies=True
        )
        
        filename = await scraper.save_results(posts)
        print(f"Example completed: {len(posts)} posts saved to {filename}")
        
    else:
        cli = FacebookScraperCLI()
        await cli.run_interactive()


if __name__ == "__main__":
    print("FACEBOOK POSTS SEARCH SCRAPER - COMPLETE VERSION")
    print("Replicates: easyapi/facebook-posts-search-scraper")
    print("\nFeatures:")
    print("- Facebook cookie authentication")
    print("- Interactive cookie setup")
    print("- Enhanced debugging capabilities")
    print("- Automatic login verification")
    print("- Complete data extraction")
    print("\nUsage:")
    print("  python facebook_scraper_complete.py                # Interactive mode")
    print("  python facebook_scraper_complete.py --setup-cookies # Cookie setup only")
    print("  python facebook_scraper_complete.py --debug         # Debug with cookies")
    print("  python facebook_scraper_complete.py --example       # Quick example")
    print("\nIMPORTANT: Set up your Facebook cookies for best results!")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nWARNING: Scraping interrupted by user")
    except Exception as e:
        print(f"\nERROR: Fatal error: {e}")
        logger.error(f"Fatal error: {e}")