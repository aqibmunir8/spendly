Add two links to the footer in @templates/base.html:

- "Terms and Conditions"
- "Privacy Policy"

Both should be plain text links, no special styling needed for now.
Point both to "#" as placeholder hrefs since the pages don't exist yet.

Do not modify anything else on the page.

git commit -m "landing: add terms and privacy links to footer”

Create a "Terms and Conditions" page for Spendly.

1. Add a new route in [@app.py](http://app.py/):
GET /terms → renders templates/terms.html
2. Create templates/terms.html with generic terms and conditions
content appropriate for a personal expense tracking app.
Include sections like: Acceptance of Terms, Use of Service,
User Data, Limitations of Liability, and Changes to Terms.
Extend base.html if it exists, otherwise match the style of
landing.html.
3. In @templates/landing.html, update the "Terms and Conditions"
footer link href from "#" to "/terms".

git commit -m "landing: add terms and conditions page and route”

Do the same as you did for the Terms and Conditions page,
but for Privacy Policy.

1. Add a new route in [@app.py](http://app.py/):
GET /privacy → renders templates/privacy.html
2. Create templates/privacy.html with generic privacy policy
content appropriate for a personal expense tracking app.
Include sections like: Data We Collect, How We Use Your Data,
Data Storage, Third Party Services, and Contact Us.
Match the style of terms.html.
3. In @templates/landing.html, update the "Privacy Policy"
footer link href from "#" to "/privacy".
4. Make sure the appearance looks like the website's theme

git commit -m "landing: add privacy policy page and route”

I've attached a screenshot of the updated Spendly hero section design.

Modify only the hero section in @templates/landing.html and @static/css/landing.css
to match this image exactly. Do not touch any other part of the page.

git commit -m "landing: redesign hero section to match mockup"

Add a modal to @templates/landing.html that opens when the user clicks
"See how it works".

Requirements:

- Clicking "See how it works" opens a modal overlay
- Modal contains an embedded YouTube video (use any placeholder YouTube URL
for now, I will replace it later)
- Video should be playable inside the modal
- Clicking the close button OR clicking outside the modal closes it
- When the modal closes, the video must stop playing (not continue in background)
- No page libraries or dependencies — vanilla JS only, since we are not
using any JS framework in this project

Do not modify any other part of the page.

git commit -m "landing: add youtube modal on see how it works click"