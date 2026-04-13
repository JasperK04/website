# This portfolio website
- Done: Tighten accessibility: ensure keyboard nav, visible focus states, and alt text coverage across templates.
- DONE: Strengthen SEO: improve how search engines crawl, index, and display your pages.
  - Add a sitemap.xml and submit it in Google Search Console and Bing Webmaster Tools.
  - Create robots.txt
  - Add canonical tags to avoid duplicate content issues across similar pages.
  - Add OpenGraph cards so shared links show rich previews.
  - Use descriptive titles/meta descriptions on each template to target search intent.
  - Ensure internal linking between related pages/projects to pass relevance signals.
- DONE: Add website logging
  - Log 404s/500s with request path and referrer to identify broken links.
  - Track basic analytics (page views, top pages, bounce) with privacy-friendly tooling.
  - Capture search queries from the site search to surface content gaps.
  - Add performance logging for slow pages (e.g., >2s TTFB) to target fixes.

# Projects

## marketplace
- DONE: Convert all uploaded images to WebP on upload to reduce bandwidth and improve load time.
- DONE: Add product search filters (price, category, condition) for better discovery.
- DONE: Add searchbar such that users can actually find products more easily.
- DONE: Create admin account from .env instead of being coded in.
- DONE: Admins can view deactivated listing and users
- DONE: Users can see their own deactivated listings and profile
- DONE: Disable buy option for deactivated accounts.
- DONE: Users should be logged out if the db is reseeded  
- DONE: Automatically Re-seed (faker) or restore (from backup) db 2x a day to prevent spam. 
  - DONE: Add info banners to user and listing creation that informs users of this.

## recipes
- Introduce three account roles: reviewer, creator, and admin with clearly scoped permissions.
  - Logged out:
    - View recipes
    - Search recipes
  - Viewers: 
    - All of the above
    - Score recipes
    - Request to be become a Creator
  - Creator:
    - All of the above
    - Create recipe drafts
    - Publish their own drafts
    - Edit their own recipes
    - Unpublish or Delete their own recipes
  - Admin:
    - All of the above
    - View unpublished/draft/deactivated recipes
    - View Deactivated Users
    - Deactivate recipes (become hidden) 
    - Deactivate users
      - Deactivates their recipes 
      - Prevents creation of new recipes
    - Reactivate users and recipes
      - undoes the above
    - Promote Viewers to Creators 
    - Demote Creators to Viewers
- Add draft/publish workflow so creators can stage recipes before public release.
- Convert all uploaded images to WebP and resize on upload to reduce bandwidth.
- Add dark mode
- Add OpenGraph cards
- Add required kitchen machines etc
- Introduce list of favorite recipes 

## fasteners
- Implement early termination such that questions stop being asked when there is only 1 result left.
- Add question ranking so the most informative questions are asked first.