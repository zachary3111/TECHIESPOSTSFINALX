#!/usr/bin/env python3
"""
Facebook Posts Search Scraper - Apify Actor Version
Main entry point for Apify platform deployment
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any

# Import Apify SDK
try:
    from apify import Actor
except ImportError:
    print("Apify SDK not found. Installing...")
    os.system("pip install apify")
    from apify import Actor

# Import our scraper
from facebook_scraper_complete import FacebookPostsScraper, FacebookCookieManager

async def main():
    """
    Main Actor function for Apify platform
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Log the input for debugging
        Actor.log.info(f"Actor input: {json.dumps(actor_input, indent=2)}")
        
        # Validate input
        search_query = actor_input.get('searchQuery', '').strip()
        search_url = actor_input.get('searchUrl', '').strip()
        
        if not search_query and not search_url:
            await Actor.fail('Either searchQuery or searchUrl must be provided')
            return
        
        if search_query and search_url:
            Actor.log.warning('Both searchQuery and searchUrl provided. Using searchQuery.')
            search_url = None
        
        # Extract parameters
        max_posts = actor_input.get('maxPosts', 10)
        post_time_range = actor_input.get('postTimeRange', '').strip() or None
        headless = actor_input.get('headless', True)
        debug = actor_input.get('debug', False)
        use_cookies = actor_input.get('useCookies', True)
        facebook_cookies = actor_input.get('facebookCookies', '').strip()
        proxy = actor_input.get('proxy', '').strip() or None
        
        # Validate maxPosts
        if not isinstance(max_posts, int) or max_posts < 1 or max_posts > 5000:
            await Actor.fail('maxPosts must be an integer between 1 and 5000')
            return
        
        # Validate postTimeRange
        if post_time_range and post_time_range not in ['24h', '7d', '30d', '90d']:
            await Actor.fail('postTimeRange must be one of: 24h, 7d, 30d, 90d')
            return
        
        Actor.log.info(f"Starting Facebook scraper with query: {search_query or search_url}")
        Actor.log.info(f"Max posts: {max_posts}, Time range: {post_time_range or 'None'}")
        
        try:
            # Set up cookies if provided
            cookie_manager = None
            if use_cookies and facebook_cookies:
                cookie_manager = FacebookCookieManager()
                try:
                    # Parse cookies from JSON string
                    cookies_data = json.loads(facebook_cookies)
                    if isinstance(cookies_data, list):
                        cookie_manager.cookies = cookies_data
                        # Save to file for the scraper to use
                        cookie_manager.save_cookies_to_file(cookies_data)
                        Actor.log.info(f"Loaded {len(cookies_data)} Facebook cookies")
                    else:
                        Actor.log.warning("Invalid cookies format. Expected JSON array.")
                        use_cookies = False
                except json.JSONDecodeError:
                    Actor.log.warning("Failed to parse Facebook cookies JSON. Proceeding without cookies.")
                    use_cookies = False
            
            # Initialize scraper
            scraper = FacebookPostsScraper(
                headless=headless,
                proxy=proxy,
                debug=debug
            )
            
            # Perform scraping
            posts = await scraper.search_posts(
                search_query=search_query,
                search_url=search_url,
                max_posts=max_posts,
                post_time_range=post_time_range,
                use_cookies=use_cookies
            )
            
            Actor.log.info(f"Successfully scraped {len(posts)} posts")
            
            # Save results to Apify dataset
            if posts:
                await Actor.push_data(posts)
                Actor.log.info(f"Pushed {len(posts)} posts to dataset")
                
                # Also save as key-value store for easy access
                await Actor.set_value('RESULTS', {
                    'totalPosts': len(posts),
                    'searchQuery': search_query,
                    'searchUrl': search_url,
                    'timeRange': post_time_range,
                    'scrapedAt': posts[0].get('time') if posts else None,
                    'posts': posts
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
                    'message': 'No posts found. Try different search terms or check if cookies are needed.'
                })
            
        except Exception as e:
            Actor.log.error(f"Scraping failed: {str(e)}")
            await Actor.fail(f"Scraping failed: {str(e)}")

if __name__ == '__main__':
    asyncio.run(main())
