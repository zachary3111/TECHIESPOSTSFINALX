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
