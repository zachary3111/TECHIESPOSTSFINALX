import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
import base64
from playwright.async_api import async_playwright, BrowserContext, Page
from apify import Actor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StealthFacebookScraper:
    def __init__(self, input_data: Dict[str, Any]):
        self.input_data = input_data
        self.max_posts = input_data.get('maxPosts', 10)
        self.search_query = input_data.get('searchQuery', '')
        self.post_time_range = input_data.get('postTimeRange', '24h')
        self.debug = input_data.get('debug', False)
        
        # Remove cookie dependency - work without authentication
        self.use_cookies = False
        
        self.browser_context = None
        self.scraped_posts = []
        
    async def setup_stealth_browser(self):
        """Setup browser with advanced anti-detection"""
        playwright = await async_playwright().start()
        
        # Force headless mode always
        headless_mode = True
        
        # Advanced stealth browser arguments
        stealth_args = [
            # Basic stealth
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            
            # Advanced anti-detection
            '--disable-blink-features=AutomationControlled',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-extensions',
            
            # Remove automation markers
            '--exclude-switches=enable-automation',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio',
            
            # Memory and performance
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            
            # Network stealth
            '--disable-features=VizDisplayCompositor,AudioServiceOutOfProcess',
            '--disable-ipc-flooding-protection',
            '--disable-web-security',
            '--allow-running-insecure-content',
            
            # Canvas and WebGL fingerprinting protection
            '--disable-accelerated-2d-canvas',
            '--disable-accelerated-jpeg-decoding',
            '--disable-accelerated-mjpeg-decode',
            '--disable-accelerated-video-decode',
            '--disable-accelerated-video-encode',
            '--disable-gpu-rasterization',
            '--disable-gpu-sandbox',
        ]
        
        launch_options = {
            'headless': headless_mode,
            'args': stealth_args,
            'ignore_default_args': [
                '--enable-automation',
                '--enable-blink-features=AutomationControlled'
            ]
        }
        
        browser = await playwright.chromium.launch(**launch_options)
        logger.info(f"Stealth browser launched (headless: {headless_mode})")
        
        # Create stealth context
        context_options = {
            'viewport': {'width': 1366, 'height': 768},  # Common resolution
            'user_agent': self.get_random_user_agent(),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': [],
            'geolocation': None,
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
            }
        }
        
        self.browser_context = await browser.new_context(**context_options)
        
        # Anti-detection JavaScript injections
        await self.inject_stealth_scripts()
        
        return self.browser_context

    def get_random_user_agent(self) -> str:
        """Get a realistic user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        return random.choice(user_agents)

    async def inject_stealth_scripts(self):
        """Inject anti-detection JavaScript"""
        stealth_script = """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Deno ? 'denied' : 'granted' }) :
                originalQuery(parameters)
        );
        
        // Mock chrome runtime
        window.chrome = {
            runtime: {},
        };
        
        // Mock chrome app
        window.chrome.app = {
            isInstalled: false,
        };
        
        // Mock chrome csi
        window.chrome.csi = function() {};
        
        // Mock chrome load times
        window.chrome.loadTimes = function() {
            return {
                commitLoadTime: 1484781004.6,
                connectionInfo: 'http/1.1',
                finishDocumentLoadTime: 1484781004.758,
                finishLoadTime: 1484781004.794,
                firstPaintAfterLoadTime: 1484781004.794,
                firstPaintTime: 1484781004.783,
                navigationType: 'Other',
                npnNegotiatedProtocol: 'unknown',
                requestTime: 1484781004.572,
                startLoadTime: 1484781004.572,
                wasAlternateProtocolAvailable: false,
                wasFetchedViaSpdy: false,
                wasNpnNegotiated: false
            };
        };
        
        // Hide CDP runtime
        delete window.console.debug;
        
        // Spoof screen properties
        Object.defineProperty(screen, 'availHeight', { get: () => 738 });
        Object.defineProperty(screen, 'availWidth', { get: () => 1366 });
        Object.defineProperty(screen, 'colorDepth', { get: () => 24 });
        Object.defineProperty(screen, 'pixelDepth', { get: () => 24 });
        
        // Random mouse movements simulation
        let mouseX = Math.random() * window.innerWidth;
        let mouseY = Math.random() * window.innerHeight;
        
        setInterval(() => {
            mouseX += (Math.random() - 0.5) * 10;
            mouseY += (Math.random() - 0.5) * 10;
            mouseX = Math.max(0, Math.min(window.innerWidth, mouseX));
            mouseY = Math.max(0, Math.min(window.innerHeight, mouseY));
        }, 100);
        """
        
        await self.browser_context.add_init_script(stealth_script)

    def build_simple_search_url(self) -> str:
        """Build simple Facebook search URL without complex filters"""
        # Use the simplest possible Facebook search URL
        base_url = "https://www.facebook.com/search/posts"
        encoded_query = quote_plus(self.search_query.strip())
        
        # Start with the most basic search
        return f"{base_url}?q={encoded_query}"

    async def human_like_navigation(self, page: Page, url: str):
        """Navigate like a human with realistic delays and behavior"""
        try:
            # Random delay before navigation
            await asyncio.sleep(random.uniform(1, 3))
            
            # Navigate to page
            response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # Check response status
            if response and response.status >= 400:
                logger.warning(f"HTTP {response.status} response")
            
            # Human-like page interaction
            await self.simulate_human_behavior(page)
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    async def simulate_human_behavior(self, page: Page):
        """Simulate realistic human browsing behavior"""
        try:
            # Random scroll simulation
            scroll_steps = random.randint(1, 3)
            for _ in range(scroll_steps):
                await page.evaluate('window.scrollBy(0, Math.random() * 300)')
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Random mouse movements
            for _ in range(random.randint(1, 3)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Random wait time
            await asyncio.sleep(random.uniform(2, 5))
            
        except Exception as e:
            logger.debug(f"Human simulation error: {e}")

    async def extract_posts_advanced(self, page: Page) -> List[Dict[str, Any]]:
        """Advanced post extraction without triggering detection"""
        posts = []
        
        try:
            logger.info("Starting advanced post extraction...")
            
            # Wait for content with multiple strategies
            await self.wait_for_content(page)
            
            # Try multiple extraction approaches
            extraction_methods = [
                self.extract_by_data_attributes,
                self.extract_by_aria_roles,
                self.extract_by_text_patterns,
                self.extract_by_dom_traversal
            ]
            
            for method in extraction_methods:
                try:
                    method_posts = await method(page)
                    if method_posts:
                        posts.extend(method_posts)
                        logger.info(f"Extracted {len(method_posts)} posts using {method.__name__}")
                        break
                except Exception as e:
                    logger.debug(f"Method {method.__name__} failed: {e}")
                    continue
            
            # Remove duplicates and limit results
            unique_posts = []
            seen_texts = set()
            
            for post in posts:
                text_key = (post.get('text', '') or '')[:100]
                if text_key and text_key not in seen_texts:
                    seen_texts.add(text_key)
                    unique_posts.append(post)
                    
                    if len(unique_posts) >= self.max_posts:
                        break
            
            logger.info(f"Successfully extracted {len(unique_posts)} unique posts")
            return unique_posts
            
        except Exception as e:
            logger.error(f"Advanced extraction failed: {e}")
            return posts

    async def wait_for_content(self, page: Page):
        """Wait for Facebook content to load"""
        selectors_to_try = [
            'div[role="main"]',
            'div[data-pagelet]',
            '#mount_0_0_V5',
            'body'
        ]
        
        for selector in selectors_to_try:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                logger.info(f"Content loaded: {selector}")
                return
            except:
                continue
        
        logger.warning("No content selectors found, proceeding anyway")

    async def extract_by_data_attributes(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts using data attributes"""
        posts = []
        
        try:
            # Look for posts by data attributes
            post_elements = await page.locator('div[data-pagelet*="FeedUnit"], div[role="article"]').all()
            
            for element in post_elements[:self.max_posts]:
                post_data = await self.extract_post_data(element, page)
                if post_data:
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.debug(f"Data attribute extraction failed: {e}")
            return []

    async def extract_by_aria_roles(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts using ARIA roles"""
        posts = []
        
        try:
            # Look for posts by ARIA roles
            post_elements = await page.locator('[role="article"], [role="feed"] > div').all()
            
            for element in post_elements[:self.max_posts]:
                post_data = await self.extract_post_data(element, page)
                if post_data:
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.debug(f"ARIA role extraction failed: {e}")
            return []

    async def extract_by_text_patterns(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts by finding text patterns"""
        posts = []
        
        try:
            # Get all text content and parse for post-like structures
            page_content = await page.content()
            
            # Use DOM traversal to find meaningful content
            content_elements = await page.locator('div, span, p').all()
            
            potential_posts = []
            for element in content_elements[:50]:
                try:
                    text = await element.inner_text()
                    if text and len(text.strip()) > 30:  # Meaningful content
                        # Check if this looks like a social media post
                        if self.looks_like_post(text):
                            post_data = {
                                'text': text.strip(),
                                'author': 'Facebook User',
                                'timestamp': datetime.now().isoformat(),
                                'likes': 0,
                                'comments': 0,
                                'shares': 0,
                                'post_url': page.url,
                                'extracted_at': datetime.now().isoformat(),
                                'extraction_method': 'text_pattern'
                            }
                            potential_posts.append(post_data)
                except:
                    continue
            
            # Filter and deduplicate
            seen_texts = set()
            for post in potential_posts:
                text_key = post['text'][:100]
                if text_key not in seen_texts and len(post['text']) > 50:
                    seen_texts.add(text_key)
                    posts.append(post)
                    
                    if len(posts) >= self.max_posts:
                        break
            
            return posts
            
        except Exception as e:
            logger.debug(f"Text pattern extraction failed: {e}")
            return []

    def looks_like_post(self, text: str) -> bool:
        """Check if text looks like a social media post"""
        # Simple heuristics to identify post-like content
        post_indicators = [
            len(text.split()) > 5,  # More than 5 words
            not text.startswith(('http', 'www')),  # Not just a URL
            '\n' not in text or text.count('\n') < 5,  # Not too many line breaks
            not text.isupper(),  # Not all caps
            not all(c.isdigit() or c.isspace() for c in text),  # Not just numbers
        ]
        
        return sum(post_indicators) >= 3

    async def extract_by_dom_traversal(self, page: Page) -> List[Dict[str, Any]]:
        """Extract by traversing DOM structure"""
        posts = []
        
        try:
            # JavaScript-based extraction
            extraction_script = """
            () => {
                const posts = [];
                const elements = document.querySelectorAll('div, article, section');
                
                for (const el of elements) {
                    const text = el.textContent;
                    if (text && text.length > 50 && text.length < 2000) {
                        // Check if this element has child elements that look like post metadata
                        const hasLinks = el.querySelector('a');
                        const hasTime = el.querySelector('time, [title*="202"]');
                        
                        if (hasLinks || hasTime) {
                            posts.push({
                                text: text.trim(),
                                html: el.innerHTML.length > 5000 ? 'too_long' : el.innerHTML
                            });
                        }
                    }
                    
                    if (posts.length >= 20) break;
                }
                
                return posts;
            }
            """
            
            js_posts = await page.evaluate(extraction_script)
            
            for js_post in js_posts[:self.max_posts]:
                post_data = {
                    'text': js_post.get('text', ''),
                    'author': 'Facebook User',
                    'timestamp': datetime.now().isoformat(),
                    'likes': 0,
                    'comments': 0,
                    'shares': 0,
                    'post_url': page.url,
                    'extracted_at': datetime.now().isoformat(),
                    'extraction_method': 'dom_traversal'
                }
                posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.debug(f"DOM traversal extraction failed: {e}")
            return []

    async def extract_post_data(self, element, page: Page) -> Optional[Dict[str, Any]]:
        """Extract data from a single post element"""
        try:
            text = await element.inner_text()
            if not text or len(text.strip()) < 20:
                return None
            
            post_data = {
                'text': text.strip(),
                'author': 'Facebook User',
                'timestamp': datetime.now().isoformat(),
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'post_url': page.url,
                'extracted_at': datetime.now().isoformat(),
                'extraction_method': 'element_extraction'
            }
            
            return post_data
            
        except Exception as e:
            logger.debug(f"Post data extraction failed: {e}")
            return None

    async def scrape_posts(self) -> List[Dict[str, Any]]:
        """Main scraping method with advanced stealth"""
        try:
            # Setup stealth browser
            await self.setup_stealth_browser()
            page = await self.browser_context.new_page()
            
            # Build simple search URL
            search_url = self.build_simple_search_url()
            logger.info(f"Navigating to: {search_url}")
            
            # Human-like navigation
            success = await self.human_like_navigation(page, search_url)
            if not success:
                logger.error("Navigation failed")
                return []
            
            # Advanced post extraction
            posts = await self.extract_posts_advanced(page)
            
            return posts
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise
        finally:
            if self.browser_context:
                try:
                    await self.browser_context.close()
                except:
                    pass

async def main():
    """Main entry point for Apify Actor"""
    async with Actor:
        # Get input
        input_data = await Actor.get_input() or {}
        logger.info(f"Input received: {input_data}")
        
        # Validate input
        search_query = input_data.get('searchQuery', '').strip()
        if not search_query:
            error_msg = "Search query is required"
            logger.error(error_msg)
            await Actor.set_status_message(error_msg)
            return
        
        # Initialize stealth scraper
        scraper = StealthFacebookScraper(input_data)
        
        try:
            # Scrape posts
            posts = await scraper.scrape_posts()
            
            # Save results
            for post in posts:
                await Actor.push_data(post)
            
            logger.info(f"Successfully scraped {len(posts)} posts")
            await Actor.set_status_message(f"Completed: scraped {len(posts)} posts")
            
        except Exception as e:
            error_msg = f"Scraping error: {str(e)}"
            logger.error(error_msg)
            await Actor.set_status_message(error_msg)

if __name__ == "__main__":
    asyncio.run(main())
