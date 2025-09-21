#!/usr/bin/env python3
"""
Facebook Posts Search Scraper - Fixed Apify Actor Version
"""

import asyncio
import json
import os
import sys
import traceback
import html

async def main():
    try:
        from apify import Actor
        
        async with Actor:
            Actor.log.info("Starting Facebook Posts Scraper...")
            
            # Get input
            actor_input = await Actor.get_input() or {}
            Actor.log.info(f"Input received: {json.dumps(actor_input, indent=2)}")
            
            # Validate basic requirements
            search_query = actor_input.get('searchQuery', '').strip()
            search_url = actor_input.get('searchUrl', '').strip()
            
            # Fix URL encoding issue
            if search_url:
                search_url = html.unescape(search_url)
                Actor.log.info(f"Fixed URL: {search_url}")
            
            if not search_query and not search_url:
                await Actor.fail("Either searchQuery or searchUrl must be provided")
                return
            
            # Import scraper after Apify setup
            try:
                from facebook_scraper_complete import FacebookPostsScraper
                Actor.log.info("Successfully imported FacebookPostsScraper")
            except ImportError as e:
                Actor.log.error(f"Failed to import scraper: {e}")
                await Actor.fail("Failed to import scraper")
                return
            
            # Handle cookies
            facebook_cookies = actor_input.get('facebookCookies', '').strip()
            use_cookies = actor_input.get('useCookies', False)  # Default to False for stability
            
            if use_cookies and facebook_cookies:
                try:
                    from facebook_scraper_complete import FacebookCookieManager
                    cookie_manager = FacebookCookieManager()
                    cookies_data = json.loads(facebook_cookies)
                    if isinstance(cookies_data, list):
                        cookie_manager.save_cookies_to_file(cookies_data)
                        Actor.log.info(f"Loaded {len(cookies_data)} Facebook cookies")
                    else:
                        Actor.log.warning("Invalid cookies format. Proceeding without cookies.")
                        use_cookies = False
                except json.JSONDecodeError as e:
                    Actor.log.warning(f"Failed to parse cookies: {e}. Proceeding without cookies.")
                    use_cookies = False
            else:
                use_cookies = False
                Actor.log.info("No cookies provided, running without authentication")
            
            # Initialize scraper with safer settings for Apify
            scraper = FacebookPostsScraper(
                headless=True,  # Always headless in Apify
                debug=False,    # Disable debug to reduce memory usage
                proxy=actor_input.get('proxy', '').strip() or None
            )
            
            Actor.log.info("Starting scraping process...")
            
            # Run scraper with error handling
            try:
                posts = await scraper.search_posts(
                    search_query=search_query,
                    search_url=search_url,
                    max_posts=min(actor_input.get('maxPosts', 10), 50),  # Limit to 50 for stability
                    post_time_range=actor_input.get('postTimeRange'),
                    use_cookies=use_cookies
                )
                
                Actor.log.info(f"Scraped {len(posts)} posts")
                
                if posts:
                    await Actor.push_data(posts)
                    Actor.log.info(f"Pushed {len(posts)} posts to dataset")
                    
                    # Save summary
                    await Actor.set_value('RESULTS', {
                        'totalPosts': len(posts),
                        'searchQuery': search_query,
                        'searchUrl': search_url,
                        'timeRange': actor_input.get('postTimeRange'),
                        'usedCookies': use_cookies,
                        'posts': posts[:3]  # Save only first 3 posts in summary
                    })
                    
                    # Log sample results
                    Actor.log.info("Sample results:")
                    for i, post in enumerate(posts[:3], 1):
                        Actor.log.info(f"Post {i}: {post.get('pageName', 'Unknown')} - {post.get('likes', 0)} likes")
                        
                else:
                    Actor.log.warning("No posts found")
                    await Actor.set_value('RESULTS', {
                        'totalPosts': 0,
                        'searchQuery': search_query,
                        'searchUrl': search_url,
                        'message': 'No posts found. Facebook may be blocking access or cookies may be needed.',
                        'usedCookies': use_cookies
                    })
                    
            except Exception as scraping_error:
                Actor.log.error(f"Scraping error: {str(scraping_error)}")
                
                # Try fallback with minimal settings
                Actor.log.info("Attempting fallback scraping...")
                try:
                    fallback_scraper = FacebookPostsScraper(
                        headless=True,
                        debug=False
                    )
                    
                    # Try simple search without cookies
                    posts = await fallback_scraper.search_posts(
                        search_query=search_query or "technology",  # Fallback query
                        max_posts=5,
                        use_cookies=False
                    )
                    
                    if posts:
                        await Actor.push_data(posts)
                        Actor.log.info(f"Fallback successful: {len(posts)} posts")
                    else:
                        await Actor.set_value('RESULTS', {
                            'error': 'Scraping failed',
                            'originalError': str(scraping_error),
                            'message': 'Both primary and fallback scraping failed'
                        })
                        
                except Exception as fallback_error:
                    Actor.log.error(f"Fallback also failed: {str(fallback_error)}")
                    await Actor.set_value('RESULTS', {
                        'error': 'Complete failure',
                        'primaryError': str(scraping_error),
                        'fallbackError': str(fallback_error)
                    })
            
    except Exception as e:
        Actor.log.error(f"Actor failed with error: {str(e)}")
        Actor.log.error(f"Traceback: {traceback.format_exc()}")
        await Actor.fail("Critical error in Actor execution")

if __name__ == '__main__':
    asyncio.run(main())
