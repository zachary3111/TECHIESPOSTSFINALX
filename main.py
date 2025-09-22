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

class MultiStrategyFacebookScraper:
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
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            '--disable-blink-features=AutomationControlled',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--exclude-switches=enable-automation',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--mute-audio',
            '--memory-pressure-off',
            '--disable-features=VizDisplayCompositor,AudioServiceOutOfProcess',
            '--disable-ipc-flooding-protection',
            '--disable-web-security',
            '--allow-running-insecure-content',
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
            'viewport': {'width': 1366, 'height': 768},
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
        
        // Mock chrome runtime
        window.chrome = {
            runtime: {},
            app: { isInstalled: false },
            csi: function() {},
            loadTimes: function() {
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
            }
        };
        
        // Hide CDP runtime
        delete window.console.debug;
        """
        
        await self.browser_context.add_init_script(stealth_script)

    def build_alternative_urls(self) -> List[str]:
        """Build multiple URL strategies to try"""
        encoded_query = quote_plus(self.search_query.strip())
        
        urls_to_try = [
            # Strategy 1: Mobile Facebook search
            f"https://m.facebook.com/search/posts/?q={encoded_query}",
            f"https://mobile.facebook.com/search/posts/?q={encoded_query}",
            
            # Strategy 2: Different desktop search formats
            f"https://www.facebook.com/search/top/?q={encoded_query}",
            f"https://www.facebook.com/search/posts/?q={encoded_query}&filters=recent",
            f"https://www.facebook.com/search/?q={encoded_query}",
            
            # Strategy 3: Public pages related to search term
            f"https://www.facebook.com/public/{encoded_query}",
            
            # Strategy 4: Hashtag-based search
            f"https://www.facebook.com/hashtag/{encoded_query}",
            
            # Strategy 5: Basic Facebook with search parameter
            f"https://www.facebook.com/?q={encoded_query}",
        ]
        
        return urls_to_try

    async def try_url_strategy(self, page: Page, url: str) -> Dict[str, Any]:
        """Try a specific URL strategy and analyze results"""
        try:
            logger.info(f"Trying URL strategy: {url}")
            
            # Navigate with timeout
            response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            
            # Analyze response
            status = response.status if response else 0
            page_title = await page.title()
            
            # Wait for content
            await asyncio.sleep(random.uniform(2, 4))
            
            # Get page content for analysis
            page_content = await page.content()
            
            result = {
                'url': url,
                'status': status,
                'title': page_title,
                'content_length': len(page_content),
                'success': False,
                'posts': []
            }
            
            # Determine if this strategy worked
            if status == 200:
                # Check for error indicators
                error_indicators = [
                    'This page isn\'t available',
                    'content is not available',
                    'Page not found',
                    'login to continue',
                    'Log in to Facebook'
                ]
                
                page_text = await page.inner_text('body')
                
                # If page doesn't contain error indicators, try extraction
                if not any(indicator.lower() in page_text.lower() for indicator in error_indicators):
                    result['success'] = True
                    posts = await self.extract_posts_from_strategy(page)
                    result['posts'] = posts
                    logger.info(f"Strategy {url} succeeded with {len(posts)} posts")
                else:
                    logger.warning(f"Strategy {url} returned error page")
            else:
                logger.warning(f"Strategy {url} returned status {status}")
            
            return result
            
        except Exception as e:
            logger.error(f"Strategy {url} failed: {e}")
            return {
                'url': url,
                'status': 0,
                'title': '',
                'content_length': 0,
                'success': False,
                'posts': [],
                'error': str(e)
            }

    async def extract_posts_from_strategy(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts from the current page regardless of strategy"""
        posts = []
        
        try:
            # Multiple extraction approaches
            extraction_methods = [
                self.extract_mobile_posts,
                self.extract_desktop_posts,
                self.extract_by_text_patterns,
                self.extract_by_semantic_analysis
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
            unique_posts = self.deduplicate_posts(posts)
            return unique_posts[:self.max_posts]
            
        except Exception as e:
            logger.error(f"Post extraction failed: {e}")
            return []

    async def extract_mobile_posts(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts from mobile Facebook"""
        posts = []
        
        try:
            # Mobile Facebook specific selectors
            mobile_selectors = [
                'div[data-ft]',  # Mobile Facebook post containers
                'article',
                'div[role="article"]',
                '.story_body_container',
                'div._5pcr',
                '._4-u2'
            ]
            
            for selector in mobile_selectors:
                elements = await page.locator(selector).all()
                if elements:
                    logger.info(f"Found {len(elements)} mobile posts with selector: {selector}")
                    
                    for element in elements[:self.max_posts]:
                        try:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 30:
                                post_data = {
                                    'text': text.strip(),
                                    'author': 'Facebook User',
                                    'timestamp': datetime.now().isoformat(),
                                    'likes': 0,
                                    'comments': 0,
                                    'shares': 0,
                                    'post_url': page.url,
                                    'extracted_at': datetime.now().isoformat(),
                                    'extraction_method': 'mobile_posts'
                                }
                                posts.append(post_data)
                        except:
                            continue
                    
                    if posts:
                        break
            
            return posts
            
        except Exception as e:
            logger.debug(f"Mobile extraction failed: {e}")
            return []

    async def extract_desktop_posts(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts from desktop Facebook"""
        posts = []
        
        try:
            # Desktop Facebook specific selectors
            desktop_selectors = [
                '[role="article"]',
                '[data-pagelet="FeedUnit"]',
                '.userContentWrapper',
                '._5jmm',
                '[data-testid="post_message"]'
            ]
            
            for selector in desktop_selectors:
                elements = await page.locator(selector).all()
                if elements:
                    logger.info(f"Found {len(elements)} desktop posts with selector: {selector}")
                    
                    for element in elements[:self.max_posts]:
                        try:
                            text = await element.inner_text()
                            if text and len(text.strip()) > 30:
                                post_data = {
                                    'text': text.strip(),
                                    'author': 'Facebook User',
                                    'timestamp': datetime.now().isoformat(),
                                    'likes': 0,
                                    'comments': 0,
                                    'shares': 0,
                                    'post_url': page.url,
                                    'extracted_at': datetime.now().isoformat(),
                                    'extraction_method': 'desktop_posts'
                                }
                                posts.append(post_data)
                        except:
                            continue
                    
                    if posts:
                        break
            
            return posts
            
        except Exception as e:
            logger.debug(f"Desktop extraction failed: {e}")
            return []

    async def extract_by_text_patterns(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts by analyzing text patterns"""
        posts = []
        
        try:
            # Get meaningful text content
            text_elements = await page.locator('div, p, span, article').all()
            
            for element in text_elements[:50]:
                try:
                    text = await element.inner_text()
                    if text and self.looks_like_social_post(text):
                        post_data = {
                            'text': text.strip(),
                            'author': 'Facebook User',
                            'timestamp': datetime.now().isoformat(),
                            'likes': 0,
                            'comments': 0,
                            'shares': 0,
                            'post_url': page.url,
                            'extracted_at': datetime.now().isoformat(),
                            'extraction_method': 'text_patterns'
                        }
                        posts.append(post_data)
                        
                        if len(posts) >= self.max_posts:
                            break
                except:
                    continue
            
            return posts
            
        except Exception as e:
            logger.debug(f"Text pattern extraction failed: {e}")
            return []

    async def extract_by_semantic_analysis(self, page: Page) -> List[Dict[str, Any]]:
        """Extract posts using semantic analysis"""
        posts = []
        
        try:
            # JavaScript-based semantic extraction
            extraction_script = """
            () => {
                const posts = [];
                const elements = document.querySelectorAll('*');
                
                for (const el of elements) {
                    const text = el.textContent;
                    
                    // Look for elements that might be posts
                    if (text && text.length > 50 && text.length < 2000) {
                        // Check for post-like characteristics
                        const hasLinks = el.querySelector('a');
                        const hasTime = text.match(/\\d{1,2}\\s+(hour|day|week|month)s?\\s+ago/i);
                        const hasHashtags = text.includes('#');
                        const hasMentions = text.includes('@');
                        
                        // Score the element
                        let score = 0;
                        if (hasLinks) score += 1;
                        if (hasTime) score += 2;
                        if (hasHashtags) score += 1;
                        if (hasMentions) score += 1;
                        
                        // If it looks like a post, add it
                        if (score >= 1 || text.split(' ').length > 10) {
                            posts.push({
                                text: text.trim(),
                                score: score
                            });
                        }
                    }
                    
                    if (posts.length >= 20) break;
                }
                
                return posts.sort((a, b) => b.score - a.score);
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
                    'extraction_method': 'semantic_analysis',
                    'semantic_score': js_post.get('score', 0)
                }
                posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.debug(f"Semantic analysis failed: {e}")
            return []

    def looks_like_social_post(self, text: str) -> bool:
        """Enhanced detection for social media posts"""
        if not text or len(text.strip()) < 20:
            return False
        
        # Enhanced heuristics
        post_indicators = [
            len(text.split()) > 5,  # Reasonable word count
            not text.startswith(('http', 'www')),  # Not just a URL
            '\n' not in text or text.count('\n') < 10,  # Not excessive line breaks
            not text.isupper(),  # Not all caps (likely not UI text)
            any(word in text.lower() for word in ['i ', 'we ', 'my ', 'our ', 'just ', 'today ', 'yesterday ']),  # Personal language
            '#' in text or '@' in text,  # Social media markers
            any(phrase in text.lower() for phrase in ['excited to', 'happy to', 'proud to', 'check out']),  # Social expressions
            not all(c.isdigit() or c.isspace() for c in text),  # Not just numbers
            'facebook' not in text.lower() or 'meta' not in text.lower()  # Not Facebook UI text
        ]
        
        return sum(post_indicators) >= 4

    def deduplicate_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate posts"""
        seen_texts = set()
        unique_posts = []
        
        for post in posts:
            text_key = post.get('text', '')[:100]  # Use first 100 chars as key
            if text_key and text_key not in seen_texts:
                seen_texts.add(text_key)
                unique_posts.append(post)
        
        return unique_posts

    async def scrape_posts(self) -> List[Dict[str, Any]]:
        """Main scraping method with multiple URL strategies"""
        try:
            # Setup stealth browser
            await self.setup_stealth_browser()
            page = await self.browser_context.new_page()
            
            # Build alternative URLs to try
            urls_to_try = self.build_alternative_urls()
            logger.info(f"Will try {len(urls_to_try)} different URL strategies")
            
            all_posts = []
            successful_strategies = []
            
            # Try each URL strategy
            for url in urls_to_try:
                try:
                    # Random delay between attempts
                    await asyncio.sleep(random.uniform(1, 3))
                    
                    result = await self.try_url_strategy(page, url)
                    
                    if result['success'] and result['posts']:
                        successful_strategies.append(result)
                        all_posts.extend(result['posts'])
                        logger.info(f"Strategy {url} found {len(result['posts'])} posts")
                        
                        # If we have enough posts, we can stop
                        if len(all_posts) >= self.max_posts:
                            break
                    
                except Exception as e:
                    logger.warning(f"Strategy {url} encountered error: {e}")
                    continue
            
            # Log strategy results
            logger.info(f"Tried {len(urls_to_try)} strategies, {len(successful_strategies)} succeeded")
            
            # Deduplicate and limit results
            unique_posts = self.deduplicate_posts(all_posts)
            final_posts = unique_posts[:self.max_posts]
            
            return final_posts
            
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
        
        # Initialize multi-strategy scraper
        scraper = MultiStrategyFacebookScraper(input_data)
        
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
